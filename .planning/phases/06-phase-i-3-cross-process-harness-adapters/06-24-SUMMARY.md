---
phase: 06-phase-i-3-cross-process-harness-adapters
plan: 24
subsystem: peering
tags: [d-impl-59, federation, naming, single-writer, admission]
requires: ["06-18", "06-19", "06-20", "06-21"]
provides:
  - "ccf.peering — the federation seam under its own name (PeeringProtocol, PeeringAdmissionGate, PeeringTrustPolicy)"
  - "ccf_runtime.peering — the transport package, A2A named as one transport of the seam"
  - "AuditAction.peering_admitted / peering_admission_refused"
  - "tests/peering/test_peering_verdict.py — D-IMPL-59 part 4 as a property"
affects:
  - "src/ccf/assembly/worker.py, src/ccf/skills/dispatch.py, src/ccf/agents/factory.py, src/ccf/controlplane/audit.py"
  - "every test module that reached the seam"
tech-stack:
  added: []
  patterns:
    - "seam package shape: <seam>/protocol.py declaring <Seam>Protocol, matching ccf/harness/protocol.py and ccf/artifacts/protocol.py"
    - "structural discovery + count guard for parametrized invariant scans over a transport package"
key-files:
  created:
    - tests/peering/test_peering_verdict.py
  modified:
    - src/ccf/peering/ (relocated from src/ccf/a2a/)
    - runtime/ccf_runtime/peering/ (relocated from runtime/ccf_runtime/a2a/)
    - src/ccf/controlplane/audit.py
    - src/ccf/assembly/worker.py
    - src/ccf/skills/dispatch.py
    - tests/peering/ (relocated from tests/a2a/)
    - tests/invariants/test_peering_single_writer.py
    - tests/crossproc/test_peering_exchange.py
decisions:
  - "ccf.peering/protocol.py chosen for the Protocol module, matching the SDK's existing seam-package convention"
  - "Gate id string values renamed a2a-* -> peering-* (mechanical surface not enumerated by the plan; see deviations)"
  - "AdmissionRecord docstring updated in place in src/ccf/peering/admission.py, not controlplane/artifacts.py (plan path defect; see deviations)"
metrics:
  duration: ~55 min
  tasks: 3
  completed: 2026-07-27
---

# Phase 06 Plan 24: Peering — the federation seam under its own name

The federation seam is now a first-class abstraction named **Peering**, whose
Protocol is `PeeringProtocol`, with A2A named as its reference transport rather
than as the concept — realizing `D-IMPL-59` parts 1–4 for the core half, as a
re-description of existing structure with nothing deleted.

## Pinned base ref

`git tag pre-peering` = **`f45a23d639816ef40f3b169194628f4669012c9b`**

06-25 must check the no-deletion constraint against **this same tag**, not
against `HEAD~1`.

## Verification path — the source that was actually exercised

The plan's `.venv/bin/python -m pytest` would have verified the **wrong tree**.
There is no `.venv` inside an agent worktree, and the main checkout's interpreter
has `ccf` **and `ccf_runtime`** installed editable against the **main** repo.
`PYTHONPATH=src` alone is insufficient — it redirects `ccf` but leaves
`ccf_runtime` resolving to `/home/parkave/ccf_code/runtime/ccf_runtime/`, which
would have silently verified the orchestrator's transports against this
worktree's core. Every run here used:

```
PYTHONPATH=src:runtime CCF_REQUIRE_HARNESSES=1 /home/parkave/ccf_code/.venv/bin/python -m pytest -q
```

Confirmed resolution:

- `ccf.__file__` = `/home/parkave/ccf_code/.claude/worktrees/agent-a34cd79fb2b6562a8/src/ccf/__init__.py`
- `ccf_runtime.__file__` = `/home/parkave/ccf_code/.claude/worktrees/agent-a34cd79fb2b6562a8/runtime/ccf_runtime/__init__.py`

**Later waves should use `PYTHONPATH=src:runtime`, not `PYTHONPATH=src`.**

## Results

| Check | Result |
|---|---|
| `pytest -q -rs` (baseline before any change) | 977 passed, 2 skipped |
| `pytest -q -rs` (final) | **983 passed, 2 skipped** — baseline + the 6 new part-4 tests |
| `mypy` | Success, 99 source files |
| `tools.lints --all` | exit 0 |
| `git diff --diff-filter=D --name-only pre-peering -- src/ runtime/ tests/` | **no output** |
| `git diff --name-only pre-peering -- src/ccf/mcp runtime/ccf_runtime/mcp/` | **no output** (part 3's scope boundary as a diff check) |
| `grep -rc "ccf\.a2a\|ccf_runtime\.a2a" src runtime tests tools` | 0 files |
| `grep -c "class PeeringProtocol" src/ccf/peering/protocol.py` | 1; unsuffixed `class Peering` declarations: 0 |
| `lf_a2a.py` / `typed_http.py` still named for their protocols | yes |

## Renames

Every move is a `git mv`; git records rename status against `pre-peering` at the
default 50% similarity threshold. The orchestrator's merge path can validate
these as intentional renames rather than data loss.

| From | To | Rename status |
|---|---|---|
| `src/ccf/a2a/__init__.py` | `src/ccf/peering/__init__.py` | R051 |
| `src/ccf/a2a/wire.py` | `src/ccf/peering/protocol.py` | R069 |
| `src/ccf/a2a/admission.py` | `src/ccf/peering/admission.py` | R092 |
| `src/ccf/a2a/identity.py` | `src/ccf/peering/identity.py` | R099 |
| `src/ccf/a2a/trust_policy.py` | `src/ccf/peering/trust_policy.py` | R089 |
| `runtime/ccf_runtime/a2a/__init__.py` | `runtime/ccf_runtime/peering/__init__.py` | R060 |
| `runtime/ccf_runtime/a2a/lf_a2a.py` | `runtime/ccf_runtime/peering/lf_a2a.py` | R092 |
| `runtime/ccf_runtime/a2a/typed_http.py` | `runtime/ccf_runtime/peering/typed_http.py` | R091 |
| `tests/a2a/test_admission.py` | `tests/peering/test_admission.py` | R092 |
| `tests/a2a/test_admission_attributability.py` | `tests/peering/test_admission_attributability.py` | R094 |
| `tests/a2a/test_admission_record.py` | `tests/peering/test_admission_record.py` | R096 |
| `tests/a2a/test_identity.py` | `tests/peering/test_identity.py` | R099 |
| `tests/a2a/test_trust_policy.py` | `tests/peering/test_trust_policy.py` | R091 |
| `tests/invariants/test_a2a_single_writer.py` | `tests/invariants/test_peering_single_writer.py` | R090 |
| `tests/crossproc/test_a2a_exchange.py` | `tests/crossproc/test_peering_exchange.py` | R094 |

Deliberately **not** renamed: `lf_a2a.py`, `typed_http.py` (a transport is
correctly named for the protocol it speaks); anything under `src/ccf/mcp*` or
`ccf_runtime/mcp/` (part 3); `AdmittedProduct`, `ingest_admitted`,
`union_lineage`, `InboundProduct`, `PeerRef` (already transport-neutral — only
their docstrings said A2A); `A2ASkillRegistry` / `A2ABinding` / `A2AInvocation`
/ `A2ASkillUnregistered` (the **skill half**, which the plan assigns to 06-25);
`tests/crossproc/servers/a2a_producer_child.py` and `lf_a2a_producer_child.py`
(child processes named for the protocol they speak, on the same reasoning as the
transport modules).

## Identifier renames

| From | To |
|---|---|
| `WireProtocol` | `PeeringProtocol` |
| `A2AAdmissionGate` | `PeeringAdmissionGate` |
| `A2ATrustPolicy` | `PeeringTrustPolicy` |
| `A2A_TRUST_POLICY` | `PEERING_TRUST_POLICY` |
| `AuditAction "a2a_admitted"` | `"peering_admitted"` |
| `AuditAction "a2a_admission_refused"` | `"peering_admission_refused"` |
| gate id values `a2a-*` | `peering-*` (see deviations) |

`AuditEvent`'s fields are unchanged — this is an enum-literal rename, not a
schema change. `ADMISSION_RECORD.class_id` remains exactly `"ccf.admission-record"`,
as D-IMPL-58's amendment ruled.

## The part-4 property, and how it was proved to bite

`tests/peering/test_peering_verdict.py` (6 tests) turns "a Peering declares trust
inputs and never the verdict" from prose into a property:

1. **`test_a_conforming_peering_cannot_produce_the_verdict`** — a purpose-built
   `_ForgingPeering` that satisfies `isinstance(..., PeeringProtocol)` and tries
   to construct an `AdmittedProduct` outside the gate raises
   `AdmissionBypassError`. Built rather than borrowed on purpose: neither shipped
   transport attempts this, so a test written against them would pass on a fabric
   with the token removed.
2. **`test_no_discovered_transport_names_the_verdict`** — parametrized over the
   *discovered* transport set, asserting no module names `AdmittedProduct`,
   `PeeringAdmissionGate` or `_ADMISSION_TOKEN` as an identifier. A third
   transport is covered on arrival rather than on remembering.
3. **`test_transport_modules_were_actually_discovered`** — the count guard, so
   (2) cannot pass vacuously.
4. **`test_the_gate_offers_exactly_one_admission_entry_point`** — "the one gate"
   as a fact about the surface, catching the `admit_fast` / `admit_trusted` fast
   path D-IMPL-16 rules out.

**Observed failure on neutering (acceptance criterion).** With
`if token is not _ADMISSION_TOKEN:` replaced by `if False:` in
`src/ccf/peering/admission.py`:

```
>       with pytest.raises(AdmissionBypassError):
E       Failed: DID NOT RAISE AdmissionBypassError
tests/peering/test_peering_verdict.py:156: Failed
1 failed, 5 passed
```

The check was restored immediately; `git diff` against the task-2 commit is empty.

## Prior-wave closures carried forward intact

- **06-18** — the attributability gate (`GATE_LINEAGE_ATTRIBUTABILITY`, the
  federated gate sequence, `_refuse_empty_operators` / `_refuse_ttl`) is
  untouched apart from the `PeeringAdmissionGate` identifier;
  `tests/gates/test_federated_gates.py` and
  `tests/peering/test_admission_attributability.py` both pass.
- **06-19** — `AdmissionRecord` stays where 06-19 put it (`peering/admission.py`),
  persistence on admission and the contract-parametrized
  `resolve_artifact` / `resolve_artifact_at_uri` path are unchanged;
  `tests/peering/test_admission_record.py` (687 lines) passes.
- **06-21** — the constructed-instance write-surface scan, its structural
  transport discovery and **both** count guards
  (`test_transport_modules_were_actually_discovered`, and the
  `TRANSPORT_BUILDERS == TRANSPORT_CLASSES` equality) survive the rename. The
  A2-scoped unforgeability wording and its inline finding ids survive
  **verbatim** in `tests/crossproc/test_peering_exchange.py`:
  `grep -cE "advisory A2\b|\(A2\)|finding A2\b"` = 2, `grep -c "unforgeable"` = 0.
  The strong form was **not** restored. 06-21's widening of the docstring scope
  to "the federation boundary" was inherited as intended, and this plan added an
  explicit note recording that 06-21 wrote it ahead of the rename.

## Deviations from Plan

### 1. [Rule 3 — Blocking] `PYTHONPATH=src` alone verifies the wrong tree

- **Found during:** Task 1, before the first edit.
- **Issue:** `ccf_runtime` resolved to the **main** repo even with
  `PYTHONPATH=src`, because the main venv's editable install covers both
  packages. Every runtime and cross-process assertion would have run against the
  orchestrator's transports.
- **Fix:** `PYTHONPATH=src:runtime` for every mypy, lint and pytest invocation,
  with both `__file__` paths confirmed inside the worktree. Baseline was
  re-established under the corrected path (977 passed either way, so no result
  was invalidated — but the exposure was real for this plan, which moves the
  runtime package).
- **Files modified:** none.

### 2. [Rule 3 — Blocking] Plan path defect: `ccf.admission-record` is not in `controlplane/artifacts.py`

- **Found during:** Task 2.
- **Issue:** `files_modified` listed `src/ccf/controlplane/artifacts.py` and an
  acceptance criterion demanded
  `grep -c 'class_id="ccf.admission-record"' src/ccf/controlplane/artifacts.py == 1`.
  The artifact class is not there and cannot be: 06-19 placed `AdmissionRecord`
  beside `InboundPayloadCeiling` in the seam's `admission.py` precisely because
  importing `ProductLineage` into `controlplane/artifacts.py` creates the real
  cycle `products.contract → controlplane.registry → controlplane.artifacts`.
- **Fix:** the `ADMISSION_RECORD` docstring was rewritten in Peering vocabulary
  **in place** at `src/ccf/peering/admission.py:465`, with `class_id` untouched.
  No runtime-only or deferred import was introduced to force the cyclic
  placement. `controlplane/artifacts.py` was not modified at all.
- **Files modified:** `src/ccf/peering/admission.py`.

### 3. [Rule 2 — Consistency of the seam's own vocabulary] Gate id values renamed

- **Found during:** Task 1.
- **Issue:** the five gate identifiers (`GATE_PAYLOAD_CEILING` … ) carried the
  *values* `"a2a-payload-ceiling"`, `"a2a-signature"`, `"a2a-contract"`,
  `"a2a-policy-binding"`, `"a2a-lineage-continuity"`. The plan's naming-surface
  table did not enumerate them. Leaving them would have had the **uniform
  Peering gate** emit refusals into operator logs naming one of its transports —
  exactly the defect class this wave exists to eliminate.
- **Fix:** renamed to `peering-*`, with the reason recorded in the comment above
  the constants. Verified no other module or test referenced the old values
  (`grep` = 0 outside their declaration), so this is not an observable contract
  break for any current consumer. Flagged here because it is a **value** rename
  the plan did not rule; the plan does assign this plan "the core half" of the
  mechanical surface.
- **Files modified:** `src/ccf/peering/admission.py`.

### 4. [Rule 3 — Blocking] `__init__.py` rewrites had to be trimmed to preserve rename status

- **Found during:** Tasks 1 and 2.
- **Issue:** the no-deletion criterion is checked with git's **default 50%**
  rename-similarity threshold. Fully rewritten package docstrings for
  `src/ccf/peering/__init__.py` (37%, then 47%, then 49%) and
  `runtime/ccf_runtime/peering/__init__.py` (47%) fell below it and surfaced as
  `D` + `A` pairs — a *reported deletion*, and therefore a merge-path blocker,
  even though no content was lost.
- **Fix:** both docstrings were condensed so the original wording is preserved
  line-for-line where it still holds, with the Peering framing added rather than
  substituted. Final: `R051` and `R060`. **This is a constraint 06-25 will hit
  too** — a wholesale docstring rewrite of a small module reads as a deletion to
  the merge gate; add to the original, do not replace it.
- **Files modified:** the two `__init__.py` files.

### 5. [Rule 1 — Cosmetic] Line-length regressions from the mechanical rename

- **Found during:** Tasks 1 and 2.
- **Issue:** `WireProtocol` → `PeeringProtocol` and `ccf.a2a` → `ccf.peering`
  each add characters, pushing seven previously-conforming docstring lines past
  88 columns.
- **Fix:** re-wrapped those seven lines only. No linter enforces line length in
  this repo (`ruff` is not installed in the venv), so this is house-style
  maintenance rather than a gate.
- **Files modified:** `src/ccf/peering/admission.py`, `src/ccf/skills/dispatch.py`,
  `runtime/ccf_runtime/peering/{__init__,lf_a2a,typed_http}.py`.

### 6. [Informational] `boot.py` still does not construct the gate

Re-verified per the plan's `read_first`: `grep -rn "PeeringAdmissionGate("`
returns only four test modules. 06-19 did not add a construction site in
`src/ccf/boot.py`, so no edit there was required.

### 7. [Informational] `tools/lints/` held no stale path constant

Swept per the plan. No rule, allowlist entry or module-prefix constant named
`ccf.a2a` or `ccf_runtime.a2a` — the only stale reference in the whole tree was a
*fixture path string* in `tools/lints/tests/test_harness_imports.py`, updated to
`runtime/ccf_runtime/peering/lf_a2a.py` / `ccf_runtime.peering.lf_a2a`. The
`cinv02-harness` carve-out (`ccf_runtime.adapters`) is unaffected, and the
negative boundary test that D-IMPL-53 requires still flags a harness import in
the transport package.

### 8. [Informational] `docs/` left to 06-22

`docs/PHASE_I3_GATE.md` and `docs/DECISIONS.md` still name `ccf_runtime.a2a` and
`test_a2a_single_writer.py`. The plan assigns recording the rename in the gate
document to **06-22**, and `DECISIONS.md` is a historical record whose prior
entries should read as they were written. Neither was touched.

## Threat Flags

None. No new network endpoint, auth path, file-access pattern or schema at a
trust boundary was introduced — this plan is a re-description of existing
structure plus one property test. The register's three entries are all
addressed: T-06-103 is now pinned by `test_peering_verdict.py` at 06-21's
scope; T-06-104's sweep found only a fixture path, with the full lint run green;
T-06-105 is accepted per the plan (pre-gate phase, no shipped audit consumers).

## Commits

| Commit | Task |
|---|---|
| `84dad4c` | Task 1 — relocate the seam to `ccf.peering`, rename the Protocol |
| `a2cc6f8` | Task 2 — reseat the transports, rename the audit verdict members |
| `20c029c` | Task 3 — reseat the tests, pin part 4 as a property |

## Self-Check: PASSED

- `tests/peering/test_peering_verdict.py` — FOUND
- `src/ccf/peering/protocol.py`, `admission.py`, `identity.py`, `trust_policy.py`, `__init__.py` — FOUND
- `runtime/ccf_runtime/peering/{__init__,lf_a2a,typed_http}.py` — FOUND
- `tests/invariants/test_peering_single_writer.py`, `tests/crossproc/test_peering_exchange.py` — FOUND
- `src/ccf/a2a/`, `runtime/ccf_runtime/a2a/`, `tests/a2a/` — absent, as intended (all moved)
- commits `84dad4c`, `a2cc6f8`, `20c029c` — FOUND in `git log`
- `git rev-parse pre-peering` resolves to `f45a23d639816ef40f3b169194628f4669012c9b` — FOUND
