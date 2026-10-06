# D-IMPL-371 — the single consolidated CLOSE review on the batch-4 candidate

**Subject reviewed:** `integration-remaining-rows` @ `5a4f40b8` (the diff from `f9b05379`: the SEC-020 final round
`row-sec-020` @ `b371df45` and SEC-022 `row-sec-022` @ `e5da0fbe`), code/tests/workflows inlined with both executor
reports and the SEC-022 pre-implementation measurement (205,348 bytes). **Reviewers:** Codex (diff only; sandbox dead,
stated), Cursor (tree, symbols resolved), Fable (tree, measured probes). **Executor:** Opus, excluded. **Date:**
2026-10-06. **Verifier:** the orchestrator re-measured or inspected every claim carrying a disposition.

**The candidate changed after the review, by two commits the review did not see and that are described here:**
`288f30bc` (one test-only correction, below) and `91fd7965` (the revert of the SEC-020 final merge, below). The
combined regression was run once more on `91fd7965`.

## Seat verdicts

| Seat | Verdict | Blocking | Read the tree? |
| --- | --- | --- | --- |
| Codex | blocking | 2 (both INFERRED) | no |
| Cursor | **READY** | 0 | yes |
| Fable | **NOT READY** | 1 (MEASURED, SEC-020) | yes, probes executed |

## Findings, verification, disposition

| # | Seat(s) | Row | Finding | Verified how | Disposition |
| --- | --- | --- | --- | --- | --- |
| F1 | Fable B-1 (BLOCKING, **measured**); Codex 2 (inferred, acquiring plans) | SEC-020 | On the **shipped paved road** (`open_product`, default class-seeded config, the row's own acquisition seam) a Π-withheld subject differs from a never-acquired one at `computed_empty` (`None` vs a traversal finding): `GovernedResolver.__call__`'s acquisition seam ingests the asked subject's evidence **before** the plan runs, and `execute_without_request_seed` cannot undo acquisition. The "by construction" docstrings on `ProjectionOutput`, the engine and the resolver are contradicted on the reference path. Fable also found that relationship hops and the `ContentAcquiringPlan` re-feed do **not** create a residual (inspected), so Codex 2's specific mechanism is not the leak; the acquisition seam is | Fable **measured** on the paved road; orchestrator accepted the measurement (the five ruled controls all pass; this is the adjacent shape the review was asked to probe) | **CONFIRMED, BLOCKING. SEC-020 PARKED** per `D-IMPL-371` ("if it fails this round, park it"). The final merge `77d5e2a9` is **reverted at `91fd7965`**; `row-sec-020` @ `b371df45` is kept as evidence (it carries the request-seed re-execution, the five controls, and the replay rehydration fix). **For Dave, two routes, neither authorized here:** (a) fix by mechanism — pin or exclude this request's acquisition from the withheld rendering (a fourth round); (b) rule the acquisition seam out of scope, narrow the docstrings, disclose the residual, and hold it as a strict-xfail control |
| F2 | Codex 1 (inferred); Cursor, Fable (measured, advisory) | SEC-022 | A second gate instance with the **default** seen-set admits a replay | Fable **measured**; Cursor inspected `PeeringAdmissionGate.__init__` | **NOT BLOCKING under the ruling.** Q14 part 2 chose "in-process by default, behind a small Protocol so a deployment with several receivers can plug a shared one"; the obligation is documented on the public how-to, **not enforced at construction**. Recorded for Dave as **SEC-022-R1**: whether to require an explicit seen-set (no default) or a boot-time check that two gates in one process share one |
| F3 | Fable A-2 (measured) | SEC-022 | Nonce scope is `(tenant, OBSERVED peer id, nonce)`; a trust policy that lists one key under two peer ids admits the same envelope twice via relabel | Fable measured | **ADVISORY, CARRIED** as **SEC-022-C-01**: scope the nonce by signing key (kid) as well, or refuse a policy that lists one key under two ids |
| F4 | Fable A-3 | SEC-022 | `observed_peer.tenant_id` is never checked (cross-tenant reuse is blocked only by the product's tenant check) | inspected | **ADVISORY, CARRIED** as **SEC-022-C-02** |
| F5 | Cursor, Fable (measured) | SEC-022 | The ES256 signature **covers** the `ccf-issuance` protected-header member: tampering nonce, `issued_at` or subject after signing, or removing the member, is refused `SignatureRefusal` | Fable measured; Cursor inspected `DetachedJwsIdentityProvider.sign`/verify | **No finding.** The mechanism's load-bearing property holds |
| F6 | Cursor, Fable | SEC-022 | A producer may post-date `issued_at` by up to the skew; a captured envelope's second presentation hits `replayed`, then `stale-issuance` after the window; cross-instance bound = min(TTL, max_age + skew) | measured/inferred | **No finding** (ruled window semantics); recorded |
| F7 | Codex 3 | SEC-022 | The replay consult runs after the other checks, so a replayed envelope presented after its window reads `stale-issuance` rather than `replayed` | inspected | **ADVISORY, by design** (nonce spent on admission only, `D-IMPL-371` measurement); carried as a disclosure |
| F8 | Codex 4, Cursor | SEC-022 | `AdmissionRecord.issuance` is required; a historical record without it no longer validates; the only out-of-tree constructor is the frozen `archive/examples/04-cross-process/run.py` | inspected; measurement found no pinned historical record | **RECORDED** ("nothing has shipped", `D-IMPL-293`); the archive is frozen (`D-IMPL-351`) and the public how-to carries a dated note |
| F9 | Cursor | SEC-022 | The pre-implementation measurement asked for a check-only consult right after verification plus the atomic spend before persistence; the shipped code spends once, after checks 3–6, before persistence | inspected | **RECORDED** as a measurement-vs-shipped difference, not a defect; the measurement note is superseded by this record |
| F10 | Cursor | SEC-022 | `IssuedAnswer`/`IssuedRequest` parity test pins field names, not the door validators; conversion in `signed_question` is fail-closed | inspected | **ADVISORY, CARRIED** as **SEC-022-C-03** |
| F11 | Fable A-4/A-5/A-6 | SEC-020/022 | Composite parents that withhold still compose children for the real subject (inferred); `_PinnedReader` pins on no shipped substrate; no tests for an unknown `schema_version` lane or a naive `issued_at` | inspected | **CARRIED** (A-4 moot while SEC-020 is parked; A-6 as **SEC-022-C-04**) |
| F12 | Cursor | both | AST / `inspect.signature` pins are implementation-shaped; the behavioral controls are the load-bearing proof | inspected | **ADVISORY, CARRIED** |
| F13 | orchestrator | SEC-024 (consequence) | `tests/skills/test_catalog.py::TestEntrySchema::test_the_retired_a2a_token_is_refused_by_name` red on the candidate; **green on `5f1dbfd6`**, red since the SEC-024 integration — it asserted the rejected input appears in the error text, which `hide_input_in_errors` now forbids by the accepted ruling. The SEC-022 executor's "pre-existing on detached base" was a detached-archive artifact | **MEASURED** on both trees | **FIXED** at `288f30bc` (test-only): the refusal is read from the structured `literal_error` on `skill_type`, the surviving member is still named, and the test now pins that the rejected value is **absent**. `tests/skills` 149 passed |

## Rejected

Codex 1 as a BLOCKING finding: it contradicts the Q14 ruling rather than the implementation (kept as F2, a ruling
question). Codex 2's mechanism (acquisition re-feed): Fable inspected and found no residual from the re-feed itself;
the measured leak is the acquisition seam (F1).

## Regression on the final candidate `91fd7965` (SEC-020 reverted, SEC-022 kept), measured once by the orchestrator

(filled from the final run)
