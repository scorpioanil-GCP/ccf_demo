---
phase: 16
slug: documentation-rewrite-the-deterministic-path-the-adoption-ar
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-09
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `16-RESEARCH.md` § *Validation Architecture* (V-1..V-10).
> The Per-Task Verification Map is filled by `gsd-planner`; everything above it
> is verified-by-execution and stable.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest` (plus `pytest-cov`; `pytest-benchmark` for `perf/` only) |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options]`, `testpaths = ["tests"]`, 8 registered markers |
| **Quick run command** | `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests -q -m "not postgres and not chroma and not neo4j and not mongo and not fluree"` |
| **Full suite command** | `make ci` (= `lint typecheck test examples docs-strict`) |
| **Gate-checker suites CI runs but `make ci` does not** | `pytest tools/lints/tests tools/publish_scan_tests tools/docs_tests -q` — **453 passed / 3 failed at HEAD** |
| **Substrate legs** | `make legs` = `leg-postgres leg-neo4j leg-mongo leg-fluree` |
| **Estimated runtime** | quick ~90s; `make ci` several minutes; `examples` job budget 20 min |

---

## Sampling Rate

- **After every task commit:** `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/examples -q` + `make lint`
- **After every plan wave:** `make ci` — **must include `docs-strict`**, the gate that catches a dangling snippet include — plus `pytest tools/lints/tests tools/publish_scan_tests tools/docs_tests -q`
- **Before `/gsd:verify-work`:** `make ci` green, the three gate-checker suites green, `make legs` green against containers, the DGX opt-in workflow dispatched once and green
- **Max feedback latency:** 120 seconds for the per-task loop

---

## Per-Task Verification Map

*Populated by `gsd-planner`. One row per task, anchored to a V-number below.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| *(pending planning)* | | | | | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Criterion Verification Map (V-1..V-10)

Every ROADMAP success criterion resolves to a mechanical check. Plans must
anchor their `must_haves` to these V-numbers.

| # | Criterion | Verification |
|---|-----------|--------------|
| **V-1** | Sections 1–3 published, each runs by one documented command; Section 4 absent, named as Phase 17's | `make docs-strict` exit 0 **and** `make examples` exit 0 **and** new `tools/docs_tests/test_documented_commands_exist.py` parsing `Makefile` `.PHONY` + the `examples:` prerequisite list against a regex over `public/**/*.md`. Section 4 absence: `grep -c "llm_packaged\|swarm_assembled" public/` hits only in prose naming Phase 17. |
| **V-2** | Section 1 invokes no agent | New `tests/examples/test_section_one_is_agent_free.py` — AST assertion over Section-1 modules: no import of `ccf.agents`, `ccf.skills`, `ccf.workflow`, `ccf.hitl`, `ccf_runtime.adapters`. **Negative control required** (inject an agent import into a copy; assert the guard refuses) per the `test_ext00_serve_output.py` pattern. |
| **V-3** | Every Section 2 client leg imports nothing from `ccf`, across all three harnesses | Upgrade `_assert_zero_ccf_imports` to an **AST** matcher (catches `importlib.import_module("ccf")`, indented imports, `__import__`) over `client_*.py`. Keep the parametrized negative control. Add an assertion that **exactly three** named harness legs exist, so a dropped leg fails rather than passes silently. |
| **V-4** | One parameterized runner; matrix asserts equivalent Context Products across six backends; `sqlite`+`memory` always-on and network-free; four DGX opt-in; no credential in tree | (a) `pytest tests/examples/test_backend_matrix.py -q` asserting `content_hash(product_sqlite) == content_hash(product_<b>)` for every backend. (b) One-runner proof: source assertion that exactly one matrix driver module exists and contains no substrate-name literal. (c) Network-free proof: example 03's socket-guard pattern (`T-08-25`) fails the run on any non-loopback socket during always-on legs. (d) Credential proof: `git grep -c "192.168.4.76" -- examples/ public/ src/ runtime/` is 0 except in an env-defaulted, value-free artifact. |
| **V-5** | `examples/00`–`08` retired; every page sourcing from them re-cut; no partial state | `make docs-strict` exit 0 is the mechanical proof for includes (`check_paths: true` makes a dangling include a build error). For the **silent half** — prose-only path refs — new `tools/docs_tests/test_no_stale_example_paths.py` extracting every `examples/…` / `tests/examples/…` token from `public/**/*.md` and asserting each resolves on disk. Also `test -d examples/00-quickstart` must fail. *Also discharges SURFACE-AUDIT A-5's mis-pointed-include gap for path targets.* |
| **V-6** | Each example separates the CCF call spine from deployment code into distinct markered regions, legible in the repo | New `tests/examples/test_spine_separation.py`: spine module exists; carries the canonical ordered marker set; every marker opened is closed; no marker region spans both modules. **Human check remains the real gate** — carry a `checkpoint:human-verify`. |
| **V-7** | Adoption-argument page names the alternatives and their lacks; worked demonstration is the UBO question | New `tools/docs_tests/test_adoption_argument.py`: page in nav and containing (case-insensitive) a contrast phrase, the three named alternatives, the four named lacks, and the literal UBO question. This is the **exact inverse of G-01's measurement** (zero hits site-wide), so before/after is mechanical, not editorial. |
| **V-8** | Gate 2 documented as assembly-path integrity, nowhere as two independently authored sets | New `tools/docs_tests/test_gate_two_wording.py`, paragraph-scoped over `public/**/*.md`: (i) every paragraph mentioning `INV-CH7-47` or "lineage strict equality" also contains "assembly-path integrity" or an explicit negation; (ii) **zero** paragraphs affirmatively assert independence — an "independent"/"independently" match adjacent to Gate 2 must carry a negation. |
| **V-9** | A-1, A-2, A-3, A-8 discharged in the published tree | **A-1:** `grep -rn "from ccf.deployment import" public/ examples/` non-empty **and** `grep -rn "from ccf\.deployment\.[a-z_]* import" examples/ public/` empty; convention page in nav. **A-2:** maintainer page in nav naming `tools/dump_surface.py`, `make surface`, `tools/assemble_surface_changes.py`, baseline immutability; `tools/publish_scan.py --pre-build` exit 0 on it. **A-3:** `grep -c` over `public/` for `load_and_boot`, `backend`, `ccf backends`, `GraphQuery`, `registry` all > 0; no page describes a `boot()` signature mismatching `inspect.signature(ccf.boot.boot)`. **A-8:** reference page contains both halves — `BootedFabric.artifacts` reachability **and** absence from `pins`/replay dimension 2 — via `tools/docs_tests/test_advisory_discharge.py`. |
| **V-10** | No fabric changed; D-02 is a ruling with no diff | `git diff --stat <phase-base>..HEAD -- src/ runtime/` shows **zero** lines changed, or only a ruled, enumerated exception list *(see Wave 0 blocker below)*. Plus `test ! -d src/ccf/unstructured`; `grep -rn "llm_packaged" src/ \| wc -l` unchanged from base; `docs/DECISIONS.md` carries the new `D-IMPL-94` entry (highest at HEAD is `D-IMPL-93`). CI-runnable as `make gate-16`, in the spirit of the retired `make gate-15.3`, asserting the permitted-change allowlist excludes `src/` and `runtime/`. |

---

## Wave 0 Requirements

**Blocking — nothing can honestly claim green until these are done:**

- [ ] **Fix the 3 pre-existing gate-checker failures:**
  - [ ] `tools/publish_scan_tests/test_docstring_leaks.py::test_no_docstring_reproduces_whitepaper_body_text` — `ProductClassDeclaration`'s docstring in `src/ccf/controlplane/artifacts.py` trips the whitepaper shingle scan with **20 hits**. ⚠ **Requires a `src/` docstring edit, colliding with criterion 10 / V-10.** Needs an explicit recorded exception — RESEARCH Q-1, Dave-facing.
  - [ ] `tools/docs_tests/test_snippet_gate.py::test_the_unmodified_source_builds_clean` — expects an `[start:ontology]` marker in `examples/00-quickstart/run.py` that no longer exists; repoint `SNIPPET_SOURCE`/`SECTION`.
  - [ ] `tools/docs_tests/test_snippet_gate.py::test_a_deleted_section_marker_fails_the_strict_build` — same repoint.
- [ ] Decide `make ci` composition — whether it gains the three gate-checker suites so *"the full local reproduction of the always-on pipeline"* becomes true (RESEARCH Q-8; `deferred-items.md` names it as two separable Phase-16 items).

**New test modules to stand up as failing-for-the-right-reason stubs:**

- [ ] `tests/examples/test_backend_matrix.py` (V-4)
- [ ] `tests/examples/test_section_one_is_agent_free.py` (V-2)
- [ ] `tests/examples/test_spine_separation.py` (V-6)
- [ ] `tools/docs_tests/test_no_stale_example_paths.py` (V-5 / A-5)
- [ ] `tools/docs_tests/test_gate_two_wording.py` (V-8)
- [ ] `tools/docs_tests/test_adoption_argument.py` (V-7)
- [ ] `tools/docs_tests/test_advisory_discharge.py` (V-9)
- [ ] `tools/docs_tests/test_documented_commands_exist.py` (V-1)

**New non-test deliverables Wave 0 must unblock:**

- [ ] **FIBO data extension** — corp→corp `hasOwnershipInterestIn` edges carrying per-edge `ownershipPercent`. Today `ownershipPercent` is an attribute of the *Party entity*, not the ownership edge, and every edge runs Party→Corporation in exactly one hop. **The UBO question the adoption argument is built on is not answerable on the shipped data.** Requirement-bearing, must land before any KYC/UBO example or page is written.
- [ ] **LangGraph** and **Claude-Agent-SDK** client legs for Section 2 — neither exists; LangGraph has no in-tree precedent at all.
- [ ] DGX opt-in job in `.github/workflows/live-legs.yml` with secret-gated fail-fast preconditions.

**Framework install:** none needed — `pytest` and the whole toolchain are present in `.venv`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Spine/deployment separation is **legible to a human reading the repository** | V-6 / criterion 6 | The structural test proves markers are present, ordered and closed; it cannot prove a reader can *see* which code is CCF and which is theirs. Dave's wording makes the human read the real gate. | Open each new example's spine and deployment modules side by side without the rendered site. Confirm a reader who has never seen CCF can name which calls are the fabric's. |
| DGX opt-in live leg is green | V-4 | `NEO4J_PASSWORD` / `PGPASSWORD` for `192.168.4.76` are **not present in this environment**. The leg cannot be proven from this machine. | Configure GitHub Actions secrets, dispatch `live-legs.yml` once, confirm green. Dave-facing prerequisite, not a code task. |
| The adoption argument is *persuasive*, not merely present | V-7 | `test_adoption_argument.py` asserts the alternatives and lacks are named; it cannot assess whether the argument lands. | Read the page cold against the UBO question. Confirm each of the four lacks cites shipped mechanism rather than asserting. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (8 new test modules + 3 pre-existing failures + FIBO extension + 2 harness legs)
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] Every plan's `must_haves` anchors to a V-number
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
