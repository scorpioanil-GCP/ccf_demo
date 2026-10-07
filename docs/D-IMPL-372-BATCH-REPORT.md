# D-IMPL-372 — batch 5: consolidated report and the candidate

**Date:** 2026-10-06, ~12:55 MST. **Branch:** `integration-batch5` from `main` @ `29a3c5a4`. **Candidate code tree:
`d3f39126`** (the branch tip carries only docs after it: the close record and this report). **`main` untouched.**
No main merge, identifier closure, tag or release. Ledger stays **13 of 29**.

## 1. Rows

| Row | Outcome | Rounds | Branch | Evidence |
| --- | --- | --- | --- | --- |
| **SEC-023** classification authority | **INTEGRATED as PARTIAL; the row stays OPEN** (the boot guard covers only parsed `PolicyFilterParametersArtifact` objects; see the close record's R1 and proposal SEC-023-P2) | 1 of 2 | `row5-sec-023` @ `5ca07a58` | 7 exploit cases + 2 boot cases red→green; 4 severings red; orchestrator's boot-check severing red; 706 regression tests; 29 example configs + banking fixture declare authority (artifacts only) |
| **SEC-013** single-writer lease | **INTEGRATED as PARTIAL; the row stays OPEN** | 1 of 2 | `row5-sec-013` @ `279be0b6` | two-process SQLite reproduction red→green; 3 severings red; orchestrator's flock→lockf severing red; **the Postgres lease has NOT been executed anywhere** (no local server; the hosted Postgres leg was skipped in every inspected run — close record X1/Y2; un-gated at Y4, result pending); network stores declare process scope — a disclosure, not enforcement |
| **LOW-01** non-ASCII bearer → 500 | **INTEGRATED** | 1 of 2 | `row5-lows` | both token sources, both doors; the stored-token outage closed; 401 byte-identical; 3 severings red |
| **LOW-02** key_id traversal | **INTEGRATED** | 2 of 2 (corrective: a stale generated report) | `row5-lows` | total allowlist before the join; 4 severings red |
| **LOW-03** cache key tenant | **INTEGRATED** | 1 of 2 | `row5-lows` | the real red case (one view, two tenant arguments); D-IMPL-36's 5-tuple restored; 2 severings red |
| **LOW-04** ignore patterns + lint | **INTEGRATED** | 1 of 2 | `row5-lows` | 8 patterns; negations and tracked files refused; the panel's `!keys/**` claim rejected by probe |
| **LOW-05** endpoint-string lint | **INTEGRATED** | 2 of 2 (corrective: split literals folded) | `row5-lows` @ `a7e392ce` | fragments + hosts; `_fold` over `+` chains, f-strings and straight-line assignments; 211 tagged modules clean; severing red |
| two disclosures | added to the security page | — | `row5-lows` | reserved entry-point denial; stdio `os.environ` pass-through |

**Parked rows:** none this batch. **Partial / OPEN:** SEC-013 and SEC-023 (above; corrected after Dave's reading).

## 2. Scope decisions consolidated here (Dave's instruction)

1. **SEC-013 integrated as partial rather than parked.** Q7 named three stores; the SQLite and Postgres mechanisms
   satisfy its named criteria and were integrated. The persistent network stores (fluree, mongo, neo4j) only
   declare process scope, which is not enforcement; the row is **not complete** and is recorded OPEN for them.
   The alternative was to park the whole row. **Executor proposal (unapproved) SEC-013-P1:** native leases for
   mongo (a lease document under a unique index) and neo4j (a unique lock node); fluree is append-only and cannot
   lease natively — what single-writer means there needs a ruling.
2. **SEC-023's completion criterion** was taken as fail-closed construction-time enforcement (Dave's correction):
   a paved-path deployment whose `PolicyFilter` names a classification attribute with no authority declaration
   refuses to boot by name. Built and integrated. Two **executor proposals (unapproved)** rode along: the
   one-declaration-per-class spec check, and not minting relationships derived from a refused entity.
3. **Frozen specimens.** SEC-023's artifact edits touched the two frozen specimens
   (`examples/cp-04-corporate-family-tree`, `examples/cp-05-credit-exposure-rollup`), whose pins forbid re-pinning
   inside a remediation phase (`D-IMPL-261`). Their configs were **reverted**; under SEC-023's boot refusal those two
   **refuse to boot** until the post-phase validation step re-pins them. The other 27 example configs keep their
   declarations (adoption of a deliberately changed surface). **The example source ids were read from each example's
   code, not confirmed against the estate**; a wrong id surfaces as refused claims on the audit log at the next
   estate run — and only there (SEC-023-C-04: `refused_assertions` has no consumer on the paved path).

## 3. Close review (`docs/D-IMPL-372-CLOSE-REVIEWS.md`)

Codex (diff only): two inferred blocking findings — the LOW-04 one **rejected by probe**, the LOW-05 one
**confirmed by probe** and closed in LOW-05's corrective round. Cursor: READY, no blocking. Fable: READY on all rows
with measured advisories. The orchestrator found two example regressions the SEC-023 executor's archive-based
baseline had hidden (the frozen-specimen pins) and fixed them by revert.

## 4. Regression and hosted CI

| Check | Result |
| --- | --- |
| broad set on `80d3b223` (21 directories, `-m "not postgres"`) | **7372 passed, 2 failed** — the two standing reds; note this local set is narrower than the hosted quick suite (which carries 12 standing reds on `main`) and excludes substrate-marked tests |
| targeted re-runs on `d3f39126` (changed areas) | lints tests + hash-transparency + surface **911 passed**; `tests/examples` **28 / 992 / 743 — identical to the base**; docs tests **320**; lint rc=0; mypy clean (244) |
| hosted CI at `80d3b223` | lint **green**, docs gate **green**; tests job: `main`'s 12 standing failures **plus** the surface-completeness red (fixed since); the Postgres leg **skipped** (close record X1) |
| hosted CI at `8d5f90b8` — [run 37528449701](https://github.com/drcastillo/ccf_code/actions/runs/37528449701) | quick suite 15 failed / 9439 passed / 3 errors (12 standing + the cp-05 six); the un-gated Postgres leg ran: 14 failed / 241 passed — newly observed, regression status undetermined (CI-COVERAGE-01, no `main` baseline); harness conformance, Neo4j, MongoDB and Fluree legs still skipped; **the focused SEC-013 step: 1 passed** (Y4) |
| hosted CI at `d3f39126` — [run 37512501630](https://github.com/drcastillo/ccf_code/actions/runs/37512501630) | lint **green**, docs gate **green**, examples the standing hw1 failure; tests job **16 failed, 9438 passed, 3 errors** against `main`'s **12 failed, 9394 passed, 0 errors**: **seven added unsuccessful tests**, six (3 errors + 3 failures) from the frozen cp-05 specimen refusing to boot after its config revert (an orchestrator-introduced regression; three end-states for Dave, close record R2) and one surface-completeness red from a wrong fragment claim (fixed in this pass). Every substrate leg **skipped** (X1) |

## 5. Severings, by the numbers

Executors ran 4 (SEC-023) + 3 (SEC-013) + 15 (lows) + 3 (LOW-05 corrective) severings, every one red with a
sha-checked restore. The orchestrator re-ran one per row by hand: SEC-023's boot check, SEC-013's flock→lockf,
LOW-01's `str` comparison, LOW-02's guard, LOW-05's `_fold`; every one red.

## 6. Carried findings (named, not fixed)

- **SEC-023-C-01** (high) a non-authoritative source that **omits** the governed attribute blanks the label with
  **no audit event** (a DoS / monitoring-evasion lever, not an escalation — measured); a second same-class rule
  without the attribute is the same channel; a docstring says "never stripped". **C-02** `admit_entity_claim`
  skips authority. **C-03** the boot check does not see `GraphQuery`-only or hand-built `deployment_operators`
  filters, hand-composed `ccf.boot.boot`, or per-request registry builds. **C-04** `refused_assertions` has no
  consumer. Executor's C2 (self-declared source ids), C4 (archive configs would refuse to boot), C5 (`perf/synth`
  ontology), C6 (same class on `valid_from`, `series_key_attribute`, the similarity corpus attribute, peered records).
- **SEC-013-C-01…C-04** a store handle can hold the lease without minting (boot denial); `":memory:"` takes a
  sidecar in the cwd; `BootToken.lease_scope` has no reader; a plain store open runs DDL unleased; plus the
  unnormalized SQLite identity, the forked-child shared lease, PgBouncer transaction pooling, `_BOOT_CACHE`.
- **LOW-01-C-01** the constant-time witness test is vacuous (source-text scan); the exploit tests are the real
  witness. **LOW-05-C-01** privately hosted / differently shaped endpoints pass (Ollama, vLLM, Vertex `:rawPredict`,
  Bedrock `/converse` without a host, Cohere v2, `google.genai`, `langchain_anthropic`, `importlib`); runtime-built
  URLs are beyond a static lint (stated). `engine.execute` never asserts `view.tenant_id == tenant_id`.
- **Process:** the demo adapter is now installed editable from the integration checkout; one executor ran a
  host-wide `pkill` of its own pytest pattern; three executor report writes were refused by the harness and relayed;
  one executor's "pre-existing" and "0 new ids" claims were confounded by an archive baseline and corrected by
  measurement.

## 7. Candidate for a main-merge decision

**Code tree `d3f39126`** on `integration-batch5` (docs tip above it). **Not ready as a whole:** SEC-023 is partial (R1) and the candidate carries three new hosted errors from the frozen-specimen revert (R2) that only Dave's ruling among (a)/(b)/(c) can resolve. Ready as they stand: LOW-01…05 and the two disclosures; SEC-013 only as the partial it is recorded as. **No further run is authorized by this report.**
