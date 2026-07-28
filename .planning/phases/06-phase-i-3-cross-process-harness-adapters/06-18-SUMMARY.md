---
phase: 06-phase-i-3-cross-process-harness-adapters
plan: 18
subsystem: products-gates, a2a-admission
tags: [gap-closure, D-IMPL-57, D-IMPL-59, INV-CH7-47, attributability]
requires:
  - ccf.products.gates.run_gates (local three-gate sequence)
  - ccf.contracts.canonical.content_hash (D-IMPL-26 addressing)
  - ccf.a2a.identity signature verification (check 2's attested address)
provides:
  - ccf.products.gates.run_federated_gates
  - ccf.products.gates.LineageAttributionRefusal
  - ccf.products.gates.GATE_LINEAGE_ATTRIBUTABILITY
  - A2AAdmissionGate._run_federated_gates (check 5, renamed and rewired)
affects:
  - docs/PHASE_I3_GATE.md and ROADMAP criterion 2 (D-IMPL-57 closure item 2 — 06-22, not this plan)
tech-stack:
  added: []
  patterns:
    - refusal-as-value carrying both sides of its mismatch
    - shared gate steps so two sequences cannot drift into two readings
key-files:
  created:
    - tests/gates/test_federated_gates.py
    - tests/a2a/test_admission_attributability.py
  modified:
    - src/ccf/products/gates.py
    - src/ccf/a2a/admission.py
decisions:
  - "D-IMPL-57 reading (a) realized as an explicit attributability gate rather than a renamed vacuous one"
  - "The contract is stated at Peering level (D-IMPL-59), so a second transport inherits it rather than restating it"
  - "Gates 1 and 3 factored into shared private steps rather than duplicated, per the plan's 'shares rather than duplicates' instruction"
metrics:
  duration: ~45m
  completed: 2026-07-27
  tasks: 3
  files: 4
---

# Phase 06 Plan 18: Federated Gate Sequence (B1 Closure) Summary

An attributability gate with a failure mode that actually fires now replaces the
vacuous strict-equality invocation on the Peering admission path: `admission`
passes check 2's verified content address as an independent witness, and a
product whose bytes differ from the bytes whose signature verified is refused.

## What Was Built

**Task 1 — `ccf.products.gates.run_federated_gates`** (commits `95d5b7f` RED,
`6855afe` GREEN). The federated form of the sequence: empty-operator guard →
attributability → TTL bounds. `LineageAttributionRefusal` carries the declared
operator plan plus **both** content addresses (`attested_address`,
`candidate_address`), per the module's existing refusal discipline.
`GATE_LINEAGE_ATTRIBUTABILITY = "lineage-attributability"` is the third gate-name
constant. The docstring states the pairing the ruling gives it —
*products admitted through a Peering are attributable; locally assembled products
are verifiable* — at Peering level, citing `D-IMPL-57` and `D-IMPL-59`, and
records the accepted consequence in Dave's own words: a compromised or buggy peer
can assert an operator plan it did not run, and the consuming fabric will admit
the product.

**Task 2 — admission stops witnessing itself** (commit `3ba090d`).
`_run_contract_gates` is renamed `_run_federated_gates` and calls
`run_federated_gates`, passing `attested_address=content_address` — the address
`admit` already computes over the verified canonical bytes. The
"**structurally vacuous here, and deliberately so**" bullet is deleted outright
and replaced by an attributability bullet stating the consequence rather than
softening it. `grep -c engine_resolved src/ccf/a2a/admission.py` == 0;
`grep -c "structurally vacuous"` == 0. The six checks keep their order.

**Task 3 — the property pinned** (commit `711b094`).
`tests/a2a/test_admission_attributability.py`, 6 tests:

1. sensitivity guard — the untampered fixture product is admitted;
2. **the tamper case** — mutating *only* `lineage.operators_invoked` and
   re-presenting under the original detached signature refuses at the **signature
   check**, which is what makes reading (a) sound rather than hoped-for;
3. **the end-to-end attributability case, driven through `admit`** — see below;
4. the refused payload parses to an *equal* product (so the refusal is about
   bytes, not about a different or malformed product);
5. the refusal is audited with `resolved=False`;
6. the refusal is a returned value, never an exception.

### The end-to-end case is reachable through `admit`, and is demonstrated there

The plan flagged this as the case the whole gate stands on. It is reachable and
the test drives it through `A2AAdmissionGate.admit` with **no call to
`run_federated_gates` in its body**:

* The peer signs a payload that is valid JSON for the contract but is not
  `canonical_bytes(product)`. The lever is **timestamp precision**, not key
  order — `canonical_bytes` sorts keys itself, so re-ordering is a no-op, while
  its fixed-microsecond RFC3339 rendering is one of several forms the contract's
  own parser accepts. A peer whose serializer trims a zero microsecond field
  produces exactly this condition without behaving maliciously.
* Signature verification **succeeds** — asserted, via a monkeypatched spy over
  `DetachedJwsIdentityProvider.verify` that records the successful return before
  the refusal is inspected. A refusal reached at the signature check instead
  would prove nothing about this gate.
* `admit` then refuses with `GATE_LINEAGE_ATTRIBUTABILITY`, and the refusal
  carries both addresses (`attested_address == signed.content_address()`,
  `candidate_address == content_hash(product)`, and they differ).

**06-23 may write the federated-sequence gate row as evidence.** The case is
reachable through the real entry point, not only through a direct call with a
hand-supplied mismatched address.

### The counterfactual, per the D-06 "a row is drafted from a failing test" discipline

Task 2's rewire was temporarily reverted (restoring
`run_gates(..., engine_resolved=product.lineage.operators_invoked)`) and the new
file re-run. Observed:

```
3 failed, 3 passed
FAILED test_a_signed_but_non_canonical_payload_is_refused_as_unattributable
FAILED test_an_attributability_refusal_is_audited_as_unresolved
FAILED test_the_refusal_is_a_returned_value_never_an_exception
E  assert isinstance(<ccf.a2a.admission.AdmittedProduct object>, LineageAttributionRefusal)
```

The vacuous gate admits the unattributable product. The file's assertions are
therefore load-bearing rather than tautological. The rewire was restored and the
full suite re-run green before committing.

## Verification

| Check | Result |
|---|---|
| `pytest` (full suite) | 955 passed, 2 skipped (baseline 940/2 + 15 new tests) |
| `mypy` (`src`, `runtime`, strict) | Success, 99 source files |
| `tools.lints --all` | exit 0 (No-Hardcoding, `@algorithmic` CINV-03, harness imports) |
| `grep -c engine_resolved src/ccf/a2a/admission.py` | 0 |
| `grep -c "structurally vacuous" src/ccf/a2a/admission.py` | 0 |
| `grep -rn "lineage-strict-equality" tests/a2a/` | 0 matches |
| `GATE_LINEAGE_ATTRIBUTABILITY` in `gates.py` | 3 occurrences |
| `D-IMPL-57` / `D-IMPL-59` in `gates.py` | 4 / 2 |

## Deviations from Plan

### 1. [Rule 3 — Blocking] The gates test directory is `tests/gates`, not `tests/products`

- **Found during:** Task 1 verification.
- **Issue:** Every acceptance criterion and `<verify>` block named
  `tests/products`; the local gate suite actually lives at
  `tests/gates/test_product_gates.py`. There is no `tests/products`.
- **Fix:** the RED file was created as `tests/gates/test_federated_gates.py` and
  every `pytest tests/products` invocation was run as `pytest tests/gates`.
- **Commit:** `95d5b7f`.

### 2. [Rule 3 — Blocking] No `.venv` inside the worktree

- **Issue:** the plan's commands are all `.venv/bin/python …`; the virtualenv
  lives in the main checkout, and the bare interpreter there resolves `ccf` to
  the **main repo's** `src`, not the worktree's — so an unprefixed run would have
  verified the wrong tree.
- **Fix:** `.venv` symlinked into the worktree (already `.gitignore`d, line 15,
  and confirmed untracked) and every command run as
  `PYTHONPATH=src .venv/bin/python …`, verified to resolve `ccf` inside the
  worktree before any test was trusted.
- **Commit:** none — no tracked file changed.

### 3. [Interpretation] Gates 1 and 3 were factored into shared private steps

The plan's Task 1 action says the new function "shares `run_gates`'s MAX_TTL
resolution and `ServableProduct` minting rather than duplicating either", while
an adjacent sentence says "without touching" the local sequence and a must-have
says the local three gates are "byte-for-byte unchanged". These cannot both hold
literally. Sharing was chosen, as the explicit instruction: `run_gates`'s
empty-operator and TTL steps moved verbatim into `_refuse_empty_operators` and
`_refuse_ttl`, which both sequences call. The local path is unchanged in
**behaviour, gate order, gate names, refusal types and raise-vs-refuse
semantics** — `tests/gates/test_product_gates.py` passes untouched, including the
"raises on a missing pinned MAX_TTL" and "resolves MAX_TTL at gate time" cases.
Duplicating the TTL bound instead would have created a second place for
INV-CH7-48 to differ between a local and a federated product, which is the
outcome the plan's "wired in rather than reimplemented" discipline exists to
prevent.

### 4. [Minor] Fixture vocabulary sources

Task 3 required every value to come from `tests/fixtures/banking/*.yaml`. Peer
id, key id, producer hash, ceiling, semver, schema/plan/version and policy regime
do (`a2a.yaml`, `controlplane.yaml`, `ontology.yaml`). **Operator keys do not** —
they are drawn from `ccf.operators.categories` (`PolicyFilter.key`,
`TraversalNeighborhood.key`, `TemporalAsOf.key`, `SimilaritySelect.key`) because
an operator key is *mechanism* declared in `/src`, not a deployment value;
restating one as a literal in the test module would be the one place a drifted
name could hide. Test instants (`BOUNDARY`, `now`) are literal test inputs, as
they are throughout the suite — never clock reads.

## Threat Register Outcomes

| Threat ID | Disposition | Outcome |
|---|---|---|
| T-06-84 (repudiation) | mitigate | attributability checked against the address the signature covered; the peer cannot deny the plan it asserted |
| T-06-85 (tampering between verification and gating) | mitigate | address equality enforced; refusal carries both addresses; **demonstrated through `admit`**, not reasoned about |
| T-06-86 (peer asserts a plan it did not run) | accept | stated explicitly in `run_federated_gates`' and `_run_federated_gates`' docstrings, in the ruling's own words |

## Known Stubs

None.

## Threat Flags

None — no new network endpoint, auth path, file access pattern, or schema change
at a trust boundary. The one contract added (`LineageAttributionRefusal`) is a
refusal value on an existing boundary.

## Out of Scope / Follow-on

`D-IMPL-57` closure item 2 — the documentation claims in
`docs/PHASE_I3_GATE.md` and ROADMAP criterion 2 — is **06-22**, per this plan's
objective, and is untouched here.

## Self-Check: PASSED

- `src/ccf/products/gates.py` — FOUND
- `src/ccf/a2a/admission.py` — FOUND
- `tests/gates/test_federated_gates.py` — FOUND
- `tests/a2a/test_admission_attributability.py` — FOUND
- commits `95d5b7f`, `6855afe`, `3ba090d`, `711b094` — all present in `git log`
