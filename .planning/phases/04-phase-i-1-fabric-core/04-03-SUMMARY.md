---
phase: 04-phase-i-1-fabric-core
plan: 03
subsystem: contracts-canonical-controlplane
tags: [contracts, canonical-serialization, control-plane, l1-signal]
requires:
  - 04-01 (packaging, pytest/mypy config, CI)
provides:
  - CCFContract base (extra=forbid, frozen) — the typed boundary base for the whole SDK
  - canonical_bytes/content_hash — the ONE canonical serializer and content-address primitive
  - EntityClaim / RelationshipClaim / LineageEntry / PassageAnchor (E, R, T, L axes, slice subset)
  - SignalEnvelope + SourceIdentity (L1 handoff artifact, D-IMPL-33)
  - SignalSourceProtocol (the single ingress seam, no graph handle)
  - ControlPlaneRegistry + ControlPlaneProtocol + ControlPlaneMissing (append-only, no-silent-default, audited)
affects:
  - every later Phase 4 plan builds against these types; no subsystem needs to invent a contract or a config path
  - composition-preservation tests (FABR-02) and replay hashing (FABR-06) compare against canonical_bytes
  - D-IMPL-26 artifact addressing is content_hash over these bytes
tech-stack:
  added: []
  patterns:
    - one canonical JSON form (sorted keys, sorted sets, RFC3339 UTC fixed precision, Decimal-not-float) as a single module nothing else may duplicate
    - content-hash-as-version-id in the Control Plane, making re-registration of identical content idempotent
    - "\"latest\" reachable only via a separately named method, so replay paths cannot drift onto a moving target by omission"
key-files:
  created:
    - src/ccf/contracts/__init__.py
    - src/ccf/contracts/base.py
    - src/ccf/contracts/canonical.py
    - src/ccf/contracts/claims.py
    - src/ccf/signal/__init__.py
    - src/ccf/signal/envelope.py
    - src/ccf/signal/source.py
    - src/ccf/controlplane/__init__.py
    - src/ccf/controlplane/registry.py
    - tests/contracts/test_base.py
    - tests/contracts/test_canonical.py
    - tests/contracts/test_claims.py
    - tests/controlplane/test_registry.py
  modified: []
decisions:
  - "Canonical float policy: floats are REJECTED (CanonicalizationError), not normalized — binary floating point is not bit-stable across platforms/backends, and bit-for-bit is the whole point. Decimal renders as a JSON string in positional notation; int renders as a JSON number."
  - "Naive datetimes are rejected rather than assumed UTC — an implicit timezone is exactly the silent default D-IMPL-38 forbids."
  - "Control Plane version ids are content_hash values (D-IMPL-26 addressing reused), not monotonic ints. Consequence: re-registering byte-identical content is idempotent and returns the existing version."
  - "SourceIdentity lives in ccf.signal.envelope and is imported by ccf.contracts.claims: L records source identity (INV-CH8-01), so lineage and the envelope must share exactly one type rather than two that can drift."
  - "PassageAnchor is generic (kind + locator) in the slice; the structured document/transcript anchor shapes of DESIGN.md §2A.4.4 arrive with the Pattern 5 pipeline plan."
  - "The registry's clock is an injected seam (defaulting to UTC wall clock) so the audit log is testable and replay-controllable."
metrics:
  duration: ~25 min
  completed: 2026-07-25
  tasks: 3
  commits: 6
---

# Phase 4 Plan 03: Slice Contracts, Canonical Serializer, Control Plane Registry Summary

Landed the three things every later Phase I.1 plan builds on: the frozen
`extra=forbid` contract base, the single canonical serialization / content-hash
utility that bit-for-bit composition and replay comparisons depend on, and the
append-only no-silent-default Control Plane registry — each built test-first per
D-15.

## What Was Built

**Task 1 — contract base and canonical serializer** (`b4dc8e9` RED,
`cd19614` GREEN). `CCFContract` fixes `extra="forbid"` and `frozen=True` once,
at the base, rather than per model: unknown fields mean producer and consumer
disagree about the contract, which is the condition replay cannot survive
quietly, and freezing is what makes a validated instance safe to
content-address. `canonical.py` defines the SDK's only canonical form —
UTF-8 JSON, sorted mapping keys, compact separators, sets sorted by each
element's own canonical bytes, RFC3339 UTC at fixed microsecond precision,
`Decimal` as a positional string. Floats, naive datetimes, non-`str` mapping
keys, and unsupported types raise `CanonicalizationError` rather than acquiring
an accidental encoding. `content_hash` is `sha256` over those bytes
(D-IMPL-26). Cross-process stability is asserted by running the hash under
three different `PYTHONHASHSEED` values in subprocesses, which is the failure
mode set iteration would otherwise hide.

**Task 2 — slice contract subset** (`f1de35d` RED, `78db888` GREEN). Exactly
the D-05 slice subset and nothing speculative. `EntityClaim` and
`RelationshipClaim` carry the bitemporal T axis (`observed_at` against
`valid_from`/`valid_to`) plus a `frozenset[LineageEntry]`; `LineageEntry` is
frozen and hashable specifically so L accumulates by set-union (INV-CH7-17)
instead of overwriting. `SignalEnvelope` implements the D-IMPL-33 schema with
the payload opaque *by type* — there is no entity or relationship field on the
envelope for an over-eager adapter to populate, which is what makes "L1 does
not interpret" structural. `SignalSourceProtocol` declares source identity and
envelope emission and, deliberately, no graph handle of any kind: adapter
isolation and single-writer are properties of the seam's shape.

**Task 3 — Control Plane registry** (`047b060` RED, `94b5ae1` GREEN).
`ControlPlaneRegistry` is append-only per key, resolves only against an
explicit `(key, version)` pin, and exposes "latest" solely through the
separately named `resolve_latest` so a replay path cannot drift onto a moving
target by leaving an argument off. A missing key or version raises
`ControlPlaneMissing`; there is no `default=` parameter and no `None` return.
Every register and resolve — *including failed resolutions* — appends an
`AuditEvent`, since an audit plane that logs only successes cannot answer what
the deployment asked for and did not have. `ControlPlaneProtocol` is the
FABR-07 extension point for a remote control plane.

## Key Implementation Details

- Version identity *is* content identity in the registry. This reuses D-IMPL-26
  addressing rather than inventing a second versioning scheme, and it makes
  re-registering byte-identical content a no-op instead of a spurious version.
- No module in this plan holds a value: no thresholds, no tables, no key names,
  no defaults. All six modules carry `__ccf_mode__ = "algorithmic"` (CINV-03)
  and none imports an LLM client or a harness.

## Deviations from Plan

**1. [Rule 3 - Blocking] `tools.lints` does not exist in this worktree**
- **Found during:** Task 1 verification
- **Issue:** All three tasks' `<verify>` blocks run
  `python -m tools.lints --all`. The lints runner is plan 04-02's deliverable —
  a sibling in the same parallel wave — so it is absent from this worktree by
  construction, not by omission.
- **Fix:** Ran `mypy --strict src` (green, 10 files) and asserted the lint
  *intents* directly instead: `__ccf_mode__ = "algorithmic"` is asserted in the
  test suite for `base`, `canonical`, and `registry`; a grep confirms all six
  source modules carry the tag and none declares a module-level numeric
  constant (CINV-01/CINV-03 by hand). The lints runner will re-verify after the
  wave merges.
- **Files modified:** none
- **Commit:** n/a (verification-only)

**2. [Rule 1 - Naming fidelity] Envelope timestamp field names**
- **Found during:** Task 2
- **Issue:** The plan text names the envelope's timestamps
  `observed_at`/`received_at`; DESIGN.md §2A.2.1 (the D-IMPL-33 ruling) names
  them `observed_time` and `ingestion_timestamp`.
- **Fix:** Used the DESIGN.md names. Whitepaper/design fidelity outranks plan
  prose (CLAUDE.md §1), and a contract field name is exactly the sort of drift
  that is cheap now and expensive after three subsystems import it.
- **Files modified:** `src/ccf/signal/envelope.py`
- **Commit:** `78db888`

## TDD Gate Compliance

Each task ran RED → GREEN with separate commits: `b4dc8e9`→`cd19614`,
`f1de35d`→`78db888`, `047b060`→`94b5ae1`. No REFACTOR commits were needed. All
three RED commits were verified failing (collection errors on absent modules)
before implementation.

## Verification

| Check | Result |
|---|---|
| `.venv/bin/pytest tests -q` | 43 passed |
| `.venv/bin/mypy --strict src` | Success: no issues found in 10 source files |
| Acceptance import line (claims + envelope + Protocol) | exit 0 |
| `extra="forbid"` and `frozen=True` in `contracts/base.py` | present |
| Order-independence (keys and sets) | asserted, passing |
| `content_hash` 64-char lowercase hex + pinned known-input digest | asserted |
| Cross-process hash stability (3 `PYTHONHASHSEED` values) | identical |
| `__ccf_mode__ = "algorithmic"` on all six src modules | present |
| Module-level numeric constants in `src/ccf` | none |
| `python -m tools.lints --all` | not runnable — 04-02 deliverable (see deviation 1) |

## Known Stubs

None. `SignalSourceProtocol` is a Protocol declaration, not a stub — its
implementations are the ingress adapters landing in later plans.

## Threat Flags

None. T-04-05 (canonical serializer tampering) is mitigated as planned by the
single-serializer + sha256 identity design plus the order-independence and
cross-process tests; T-04-06 (cross-tenant spoofing) by `tenant_id` being
required and validated on `SignalEnvelope` and on every claim type.

## Self-Check: PASSED

All 13 created files exist on disk; all six commit hashes (`b4dc8e9`,
`cd19614`, `f1de35d`, `78db888`, `047b060`, `94b5ae1`) are present in
`git log`. Working tree clean.
