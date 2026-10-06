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

(filled: hosted CI)
