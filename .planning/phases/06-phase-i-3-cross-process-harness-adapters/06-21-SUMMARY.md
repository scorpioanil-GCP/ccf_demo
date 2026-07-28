---
phase: 06-phase-i-3-cross-process-harness-adapters
plan: 21
subsystem: cross-process-federation
tags: [invariants, single-writer, a2a, admission, d-21, gap-closure]
requires:
  - ccf_runtime.a2a.lf_a2a
  - ccf_runtime.a2a.typed_http
  - ccf.a2a.admission
provides:
  - instance-scan coverage of every shipped A2A transport, the D-IMPL-14 default included
  - a scoped AdmittedProduct unforgeability claim, pinned by a test
affects:
  - docs/PHASE_I3_GATE.md rows 3 and 6 (wording, applied by 06-22)
tech-stack:
  added: []
  patterns:
    - structural discovery of transport classes plus a builder table, guarded by a count assertion
    - claim-scoping (D-21) enforced by a two-edge test rather than by prose
key-files:
  created: []
  modified:
    - tests/invariants/test_a2a_single_writer.py
    - tests/crossproc/test_a2a_exchange.py
decisions:
  - "A1 closed by widening the instance scan structurally, not by adding a second hand-written test — a third transport joins by being discovered"
  - "A2 closed by bounding the claim, not deleting it: src/ccf/a2a/admission.py untouched; the token's justification stands, its overstatement does not"
metrics:
  duration: ~35 min
  completed: 2026-07-27
  tasks: 2
  files_modified: 2
  tests_added: 3
requirements: [XPRC-02]
---

# Phase 06 Plan 21: Close advisories A1 and A2 Summary

Both advisories were the same defect class this phase already recorded once — evidence
that reads stronger than it is — and both are now closed by a test rather than by a note:
the single-writer instance scan covers **every** shipped transport including the D-IMPL-14
default, and the `AdmittedProduct` claim is bounded at the scope Python's import model
actually supports.

## What Was Built

### Task 1 — the instance scan now covers the federation boundary, not one protocol (A1)

`tests/invariants/test_a2a_single_writer.py` constructed only `TypedHttpWire`, so `lf_a2a`
— the transport a deployment gets *by default* — carried only the weaker half of the
evidence. Three changes:

- **`_transport_classes()`** discovers `WireProtocol`-shaped classes structurally (defined
  in a discovered module, offering both `emit` and `receive`), mirroring why
  `_transport_modules()` discovers rather than lists. A hand-listed pair is a pair a third
  transport can be added beside without joining — which is precisely how A1 happened.
- **`TRANSPORT_BUILDERS`**, keyed by class rather than by name so a rename cannot silently
  drop a leg. `test_a_constructed_transport_holds_no_fabric_write_surface` is now
  parametrized over `TRANSPORT_CLASSES`; the suite shows two legs, `[TypedHttpWire]` and
  `[LfA2AWire]`.
- **`test_every_discovered_transport_is_actually_constructed`** — the count guard, the same
  guard `test_transport_modules_were_actually_discovered` already applies to the source
  scan. It also asserts positively that a class from `lf_a2a` is in the scanned set.

Every value handed to either constructor comes from `tests/fixtures/banking/a2a.yaml`
(`lf_a2a.rpc_path`, `lf_a2a.card.*`, `consumer.max_request_bytes`,
`consumer.receive_path`, `peers.first.peer_id`). No endpoint, card field, peer id or
ceiling is authored in the test module (CINV-01). No peer is contacted and no port is
bound — constructing the object is the whole of what an attribute scan needs.

The module docstring's scope sentence is restated over the **federation boundary** rather
than over A2A specifically, so D-IMPL-59's second transport inherits the scan by being
discovered rather than needing a test of its own, and 06-24's rename of this module to
`tests/invariants/test_peering_single_writer.py` inherits the widening intact. Identifiers
were deliberately *not* renamed here — 06-24 changes the vocabulary wholesale.

**Count-guard falsification, as run.** Stubbing the discovery set to a single transport and
calling the guard directly:

```
OBSERVED FAILURE: 2 transport(s) are constructed but 1 were discovered:
built ['LfA2AWire', 'TypedHttpWire'], discovered ['LfA2AWire']
```

Both numbers and both name-lists are in the message, so the failure names the gap rather
than merely reporting one.

### Task 2 — the AdmittedProduct claim, bounded (A2)

`_ADMISSION_TOKEN` is importable, so `AdmittedProduct` *is* forgeable by any module willing
to name a private member. Per D-21 the claim is scoped, not deleted:

- **`test_the_unforgeability_claim_is_scoped_to_the_unforced_path`** asserts both edges of
  the scope: token withheld → `AdmissionBypassError`; private token imported and passed →
  construction succeeds. A future reader cannot upgrade the wording without a red suite.
- The word `unforgeable` is now absent from the module (0 occurrences). The honest half
  stays and is stated in its place: *no unforced path exists, and every forced path fails
  at construction; forging requires naming a private member of `ccf.a2a.admission`.*
- The finding id `A2` is carried inline on the re-scoped docstring, so the weaker sentence
  is traceable to the finding that weakened it.
- `ingest_admitted`'s declared-annotation assertion is unchanged. Both halves of gate row 6
  stay; only one is re-scoped.

`src/ccf/a2a/admission.py` is deliberately untouched. Its module docstring's argument for
*why* the token earns its place against Dave's I.2 D-12 counter-precedent is sound, and it
already states the D-21-compliant sentence. What overclaimed was the gate document's
stronger restatement.

## Wording handed to 06-22

### Gate row 6 — proposed replacement, verbatim

Replace the row-6 claim cell:

> **An inbound A2A product is not offerable to L2 unless the Control Plane admitted it — a type error, not a discipline**

with:

> **An inbound A2A product is not offerable to L2 unless the Control Plane admitted it — a type error on every unforced path**

and replace, in the same row's evidence cell:

> asserts both the declared annotation and that `AdmittedProduct` is unforgeable

with:

> asserts both the declared annotation and that every construction not carrying the gate's token fails at construction; `test_the_unforgeability_claim_is_scoped_to_the_unforced_path` pins the boundary of that claim — `_ADMISSION_TOKEN` is importable, so forging requires naming a private member of `ccf.a2a.admission`, which Python permits and no runtime check can prevent (advisory A2, D-21)

### Gate row 3 — the claim 06-22 may now strengthen

The single-writer instance scan is no longer "one constructed transport". Row 3 may state
that **every** transport `ccf_runtime.a2a` ships is constructed and attribute-scanned, the
D-IMPL-14 default `LfA2AWire` included, with the set discovered structurally and a count
guard failing when construction coverage falls behind discovery. This is a
claim-*strengthening* edit backed by new coverage, which is why it is recorded here rather
than made silently.

## Verification

| Check | Result |
|---|---|
| `pytest tests/invariants/test_a2a_single_writer.py` | 15 passed (was 13) |
| Instance scan legs | `[TypedHttpWire]`, `[LfA2AWire]` — 2 transports |
| `grep -c "lf_a2a" tests/invariants/test_a2a_single_writer.py` | 4 (≥ 1 required) |
| Count guard falsification | fails as quoted above when discovery is stubbed to one |
| `pytest tests/invariants` | 61 passed, 2 skipped |
| `pytest tests/crossproc tests/invariants` | 100 passed, 2 skipped |
| `grep -c "unforgeable" tests/crossproc/test_a2a_exchange.py` | 0 |
| `grep -cE "advisory A2\b\|\(A2\)\|finding A2\b" …` | 2 (≥ 1 required) |
| `python -m tools.lints --all` | exit 0, no output |
| `pytest -q` (full suite) | **943 passed, 2 skipped** — baseline 940/2 plus exactly the 3 tests added; no regression |

New test name contains both `scope` and `forced`
(`test_the_unforgeability_claim_is_scoped_to_the_unforced_path`) and asserts both branches.

mypy is configured over `src` and `runtime` only (`pyproject.toml` `files = ["src",
"runtime"]`), so no test-module type gate applies; neither task touched `src` or `runtime`.

## Deviations from Plan

None. Both tasks executed as written. Two wording notes worth recording as
non-deviations:

- The plan's acceptance criterion `grep -c "unforgeable" == 0` required removing two
  *meta* uses of the adjective (a docstring quoting the word it was retiring, and a
  "what would fail here" clause). Both were reworded rather than the criterion relaxed —
  "the stronger adjective is deliberately absent", and "closing the forced path so that no
  construction outside the gate succeeds at all". The function name retains
  `unforgeability`, which the criterion's pattern does not match and which reads correctly:
  the test is *about* the claim, and does not make it.
- Task 1's docstring edit is claim-strengthening, permitted by the plan and backed by the
  new coverage. Recorded above under "Gate row 3" so 06-22 reflects it rather than
  inventing prose.

## Known Stubs

None.

## Threat Flags

None. No new network endpoint, auth path, file access pattern or schema change — both
tasks are test-only. `T-06-90` (a default transport holding a write surface under a private
attribute) is now mitigated by the widened instance scan; `T-06-91` (forging via
`_ADMISSION_TOKEN`) remains **accepted**, and the acceptance is now pinned by a test rather
than asserted in prose.

## Commits

| Task | Commit | Description |
|---|---|---|
| 1 | `27e39ca` | test(06-21): instance-scan every shipped A2A transport, LF A2A default included (A1) |
| 2 | `c56209e` | test(06-21): scope the AdmittedProduct claim to what Python supports (A2) |

## Self-Check: PASSED

- `tests/invariants/test_a2a_single_writer.py` — FOUND
- `tests/crossproc/test_a2a_exchange.py` — FOUND
- commit `27e39ca` — FOUND
- commit `c56209e` — FOUND
