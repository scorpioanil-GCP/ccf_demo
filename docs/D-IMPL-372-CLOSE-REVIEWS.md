# D-IMPL-372 — the single consolidated CLOSE review on the batch-5 candidate

**Subject reviewed:** `integration-batch5` @ `80d3b223` (the diff from `main` @ `29a3c5a4`: SEC-023 `row5-sec-023` @
`5ca07a58`; SEC-013 PARTIAL `row5-sec-013` @ `279be0b6`; LOW-01…05 `row5-lows` @ `87f7a7ff`), code/tests inlined with
the three executor reports (the three measurements appended for Fable; the CLI seats received the prompt without
them). **Reviewers:** Codex (diff only; sandbox dead, stated), Cursor (tree), Fable (tree, measured probes).
**Executor:** Opus, excluded. **Date:** 2026-10-06. **Verifier:** the orchestrator probed or inspected every claim
carrying a disposition.

**The candidate changed after the review, by commits described here:** `273bb7e0`/`d0867892` (the frozen-specimen
reverts, F13) and `d3f39126` (the LOW-05 corrective round, F2). The code tree of the final candidate is `d3f39126`.

## Seat verdicts

| Seat | Verdict | Blocking | Read the tree? |
| --- | --- | --- | --- |
| Codex | NOT READY on LOW-04, LOW-05 | 2 (INFERRED) — one REJECTED by probe, one CONFIRMED by probe | no |
| Cursor | READY (SEC-023, lows); SEC-013 as PARTIAL | 0 | yes |
| Fable | READY all rows; SEC-013 as PARTIAL | 0 (measured advisories) | yes, probes executed |

## Findings, verification, disposition

| # | Seat(s) | Row | Finding | Verified how | Disposition |
| --- | --- | --- | --- | --- | --- |
| F1 | Codex | LOW-04 | The ignore lint's negation check looks only at the last path segment, so `!keys/**` re-includes key material unseen | **PROBED**: a `.gitignore` with all patterns plus `!keys/**` → the lint reports `negation '!keys/**' re-includes key material`; git indeed re-includes `keys/a.jwk` | **REJECTED.** The lint already refuses the shape |
| F2 | Codex | LOW-05 | Split literals (`"https://" + "api." + "anthropic.com" + "/v1/" + "messages"`) draw 0 findings | **PROBED**: 0 findings vs 1 for the single-literal control | **CONFIRMED.** Same class as the pilot's lint-grammar holes → **LOW-05's corrective round**: `_fold` joins `+` chains and whole f-strings and follows straight-line assignments; re-verified by the orchestrator (split 1, two-assignment 2, non-model split control 0; disabling `_fold` → 18 of 25 red); integrated at `d3f39126` |
| F3 | Fable (measured), Cursor | SEC-023 | **Omission path:** a non-authoritative source that OMITS the governed attribute still supersedes the attribute set and blanks the label with **zero audit event and zero `refused_assertions`**; the spec validator admits a second same-class rule without the attribute as a route to the same silent blanking; a docstring says the attribute is "never stripped". Omission is a DoS / monitoring-evasion lever, not an escalation (every pushdown treats an absent attribute as never-permitted — measured) | Fable measured; Cursor inspected | **ADVISORY (high), CARRIED** as **SEC-023-C-01**: record absence-supersession as an audited event, require every rule of a governed class to carry the attribute under the same authorities, correct the docstring |
| F4 | Cursor | SEC-023 | `admit_entity_claim` (the low road) writes straight through without `_judge_authority`; no `src` caller; examples use `admit_relationship_claim` | inspected | **ADVISORY, CARRIED** as **SEC-023-C-02** |
| F5 | Cursor | SEC-023 | The boot check does not see a `GraphQuery`-only or hand-built `deployment_operators` `PolicyFilter` (no `PolicyFilterParametersArtifact`) | inspected | **ADVISORY, CARRIED** as **SEC-023-C-03** (adjacent to the executor's C3) |
| F6 | Fable | SEC-023 | `IngestResult.refused_assertions` has no consumer; `product.py`'s acquisition seam discards it, so a wrong example source id is visible only on the audit log, never in a replay record | Fable measured | **ADVISORY, CARRIED** as **SEC-023-C-04** |
| F7 | Cursor, Fable (measured) | SEC-013 | Anyone holding a store handle can call `BackendStore.writer_lease` and hold the flock without minting → a boot denial, not a second writer; `":memory:"` SQLite takes a sidecar in the cwd; `BootToken.lease_scope` has no reader anywhere (the declared scope is unread configuration); a plain store open runs DDL unleased | Fable measured failure-after-mint and close both release; no writer constructible without the mint | **ADVISORY, CARRIED** as **SEC-013-C-01…C-04**; the row is **PARTIAL and OPEN** by Dave's correction regardless |
| F8 | Cursor, Fable (measured) | LOW-01 | `test_the_module_still_compares_in_constant_time` asserts `"hmac.compare_digest" in inspect.getsource(...)` — the docstring contains the phrase three times, so swapping `_tokens_match` to `==` keeps it green | Fable measured | **ADVISORY, CARRIED** as **LOW-01-C-01**: pin via `__code__.co_names` or AST. The exploit tests remain the real witness |
| F9 | Fable (measured), Cursor | LOW-05 | Privately hosted or differently-shaped model endpoints pass: Ollama `/api/generate`, `/api/chat`; vLLM `/v1/completions`, `/v1/embeddings`; Vertex `:rawPredict`; Bedrock `/converse` without a host literal; Cohere v2; `google.genai`, `langchain_anthropic`, `importlib`-loaded `anthropic`; an internal proxy host | Fable measured | **ADVISORY, CARRIED** as **LOW-05-C-01** with the fragment and module list; the acceptance was literal/fragment coverage, stated as such |
| F10 | Cursor | SEC-013 | Demo adapter reinstalled editable from the integration checkout (merge hygiene) | — | **RECORDED** (the shared venv's demo adapter now points at `/home/parkave/ccf_wt/mainwt/tests/fixtures/ccf-demo-adapter`) |
| F11 | all | all | No executor report contradicts the diff on the security claims | — | noted |
| F12 | orchestrator | SEC-023 | The executor's examples baseline was a `git archive` export where 21 git-dependent tests fail, so its "0 new failing ids" was confounded; on the real pre-batch tree the candidate had **2 new example reds** | **MEASURED**: failing-id diff against `5f1dbfd6` | see F13 |
| F13 | orchestrator | SEC-023 / D-IMPL-261 | The two new reds were the **frozen-specimen pins** of `examples/cp-04-corporate-family-tree` and `examples/cp-05-credit-exposure-rollup` (`test_the_specimen_is_untouched` diffs the directory against the base): SEC-023's config edits touched frozen specimens; re-pinning inside a remediation phase is forbidden by `D-IMPL-261` | **MEASURED** (pins green after the reverts) | **FIXED** at `273bb7e0`: the two specimens' configs reverted to `main`'s; cp-04-canonical's legitimate edit restored. **Recorded as a finding:** under SEC-023's boot refusal those two frozen specimens **refuse to boot** until the post-phase validation step re-pins them. The other 27 example configs keep their authority declarations (adoption of a deliberately changed surface, allowed by `D-IMPL-261`); their source ids were read from code, not confirmed against the estate |
| F14 | orchestrator | SEC-023 | The executor ran a host-wide `pkill -f "pytest -p no:cacheprovider -q -x"` once | reported | **RECORDED** as a process incident; the other executors' reports show no aborted run |

## Rejected

F1 (Codex, LOW-04), by probe.

## Regression on the final candidate `d3f39126`, measured by the orchestrator

| Check | Result |
| --- | --- |
| broad set on `80d3b223` (21 directories incl. assembly, operators, deployment, integration, conformance; `-m "not postgres"`) | **7372 passed, 2 failed, 111 skipped** — the two standing reds that predate every batch |
| targeted re-runs on `d3f39126` (the only code change after `80d3b223` is the LOW-05 lint; the only other change is two example configs) | `tools/lints/tests` + hash-transparency + surface **911 passed**; `tests/examples` **28 failed, 992 passed, 743 skipped — identical to the base**; `tools/docs_tests` **320 passed**; `tools.lints --all` rc=0; `mypy` clean (244 files) |
| the Postgres lease | **not run locally** (no server); the hosted CI Postgres leg is the proof — see the batch report |

## Hosted CI (GitHub, `ci.yml` on every push), read per job

| Commit | lint + strict types | docs gate | tests (python 3.12) | examples suite |
| --- | --- | --- | --- | --- |
| `main` @ `29a3c5a4` (baseline) | success | success | failure: one node, `perf/suites/micro/test_factory.py::test_task_factory_construct` | failure: the hw1 reference client exits 1 (standing) |
| `ea966348` (SEC-023 integrated) | success | **failure** (retirement report stale between docs commits; regenerated at `0c407c83`) | failure: the same single node | the same |
| `80d3b223` (all three rows) | success | success | failure: **the same single node** | the same |
| `d3f39126` (final code) — run [37512501630](https://github.com/drcastillo/ccf_code/actions/runs/37512501630) | success | success | **failure: the baseline perf node PLUS three NEW errors** — `ERROR at setup` of `tests/products/test_cp05_canonical_path.py::test_cp05s_declarations_boot_and_populate_offline`, `::test_the_canonical_path_serves_cp05s_declared_family`, `::test_the_gate_seam_is_live_on_cp05s_path` (`UngovernedClassificationAttribute` booting the frozen cp-05 specimen) | the standing hw1 failure |
| `05dcfcce` (docs tip) — run [37514536308](https://github.com/drcastillo/ccf_code/actions/runs/37514536308) | success | success | the same (code identical to `d3f39126`) | the same |

**The Postgres lease ran on the hosted leg.** The tests job binds a `postgres:16` service and sets
`CCF_REQUIRE_POSTGRES=1`, under which a `postgres`-marked test **fails** rather than skips when no server answers;
the job's failing set at `80d3b223` is exactly the baseline's single perf node, so SEC-013's Postgres twin
(`tests/graph/test_single_writer_across_processes.py`, the `postgres` case) executed against a live server and passed.
It was not run locally (no disposable server).

## Corrections after Dave's reading of this record (2026-10-06 12:12 MST)

**R1 — SEC-023 is NOT complete; it is PARTIAL / OPEN.** The construction-time guard
(`src/ccf/deployment/manifest.py::_refuse_ungoverned_classification`) inspects only parsed
`PolicyFilterParametersArtifact` objects on the two paved doors. The classification paths it does not see (F5, and the
executor's C3) are: a `GraphQuery`-only classification map; a hand-built `PolicyFilter` supplied through
`deployment_operators`; a hand-composed `ccf.boot.boot`; a per-request `build_operator_registry` without a boot.
Dave's criterion — *"wherever classification controls access"* — requires each of those to **enforce authority,
refuse, or carry an explicitly approved exclusion**. None does today, so the completion claim in this record and the
batch report is **withdrawn**. **Executor-side proposal (unapproved), SEC-023-P2, the smallest construction-time
placement that covers them all:** move the authority check to the **construction of the consumer** — a
`PolicyFilter` (its parameters) or a `GraphQuery` that carries a classification map refuses to be built unless the
governing `EntityResolutionSpec` declares authority for every attribute it names; the artifact-time door check stays
as the early refusal. That covers hand-built operators, `GraphQuery`-only maps, hand-composed boots and per-request
builds by construction, because all of them construct the consumer. SEC-023's one remaining corrective round is
available for it on Dave's word; no exclusion is proposed.

**R2 — the frozen-specimen revert's compatibility consequence, recorded explicitly.** Reverting the configs of
`examples/cp-04-corporate-family-tree` and `examples/cp-05-credit-exposure-rollup` preserved their specimen pins
(`D-IMPL-261`) **and left those two examples unable to boot** under SEC-023's refusal (`cp-05-demo/policy.principal-subgraph`
admits `exposure_anchor` with no authority declaration). This is not only a future consequence: three tests in
`tests/products/test_cp05_canonical_path.py` boot the cp-05 specimen offline (`fluree`-marked, **no** environment
skip, "a stop-rule test"), and they **ERROR at setup on the candidate**, locally and on the hosted runner (above). They
were green at `80d3b223`, before the revert, and the orchestrator's targeted re-runs after the revert covered
`tests/examples` but not `tests/products`, which is how they were missed. **Pin preservation and a working example
cannot both hold on this candidate.** The three end-states, for Dave: (a) keep the pins, carry the three reds and the
non-booting specimens to the post-phase validation step; (b) restore the executor's declarations on the two frozen
specimens (working examples, pins moved — a re-pin inside the phase, which `D-IMPL-261` forbids without a ruling);
(c) an explicitly approved exclusion of frozen specimens from the boot refusal (weakens enforcement where
classification controls access — not recommended for a bank). The candidate as pushed is state (a).

**R3 — final-commit CI evidence** is in the table above with run URLs; the two docs commits after `d3f39126` ran the
same code and show the same results.

**R4 — SEC-013 stays PARTIAL / OPEN** for the persistent network stores; every follow-on in this record (SEC-013-P1,
SEC-023's two riders, SEC-023-P2) is an **unapproved proposal**.
