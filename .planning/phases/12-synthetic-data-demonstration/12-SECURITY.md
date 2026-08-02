---
phase: 12
slug: synthetic-data-demonstration
status: verified
threats_open: 0
asvs_level: 1
created: 2026-08-02
---

# Phase 12 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| scenario.yaml → generator | self-authored versioned artifact interpreted by example code; no external input | schemas, identifiers, vocabulary, pins |
| generator → SQLite files | file writes into a tempfile working dir only | synthetic rows |
| SQLite rows → L1 envelopes | self-generated data crossing into the fabric via typed SignalEnvelope | row payloads |
| Context Product → skill callable | governed typed payload; validated at contract gates | payment-network payload |
| --live prompt → external LLM | opt-in only; output is narration, never feeds detection or assertions | rendered prompt + synthetic detection outcome |
| docs/Makefile | no runtime trust boundary; build/docs surface only | literal-include paths |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-12-01 | Tampering | SQLite writes/reads in generator.py | mitigate | Centralized escaped-quoting helper `sql_identifier` (generator.py:51-59, doubles embedded `"`); used at every identifier site — checksum read (generator.py:83-86), CREATE TABLE / INSERT (generator.py:145-153); values travel only as `?` bound parameters via `executemany` (generator.py:148, 152-154). No value ever interpolated into SQL text | closed |
| T-12-02 | Information Disclosure | generated data | accept | Fully synthetic banking data, no real PII by construction — all names/ids are lexicon-composed from scenario.yaml (generator.py:170-196); see Accepted Risks | closed |
| T-12-03 | Tampering | ingest SQL reads in run.py | mitigate | Identifiers quoted through the same `generator.sql_identifier` helper (run.py:235-238) and explicit `ORDER BY {id_sql}` for determinism (run.py:240-244); no value interpolation in the SELECT | closed |
| T-12-04 | Elevation of Privilege | graph writes | mitigate | Single-writer honored: the only graph write path is `handle.worker.ingest(envelope)` (run.py:710-711); run.py imports no graph writer (import block run.py:52-118 — only `ReplayWriter`, an ArtifactStore serializer at run.py:106/1046, not a graph writer); CINV writer lint green (`python -m tools.lints --all` exit 0, 12-02/12-03 SUMMARYs) | closed |
| T-12-05 | Spoofing | skill invocation | mitigate | Catalog + grant + ledger path only (§6.2): `SkillCatalog.register(entry)` (run.py:944-948), `GrantLedger.request(grant, definition=…, actor=…)` (run.py:970-978), factory-only agent construction with `bound_skills=ledger.bound_view(definition_hash)` (run.py:962-968), invocation exclusively via `agent.invoke_skill(...)` (run.py:985-987). The callable is reached only through `CallableRegistry` under the artifact-declared `callable_ref` (run.py:955-961). Stage-2 baseline calls the detection function directly (run.py:668) — by design outside the skill boundary: it is the raw-data contrast, not a fabric-governed invocation | closed |
| T-12-06 | Information Disclosure | --live LLM call | accept | Opt-in only: `httpx`/`os` imports deferred inside `_live_narration` (run.py:485-489); reached solely via the `--live` argparse flag (run.py:1132-1141) after the deterministic run completes (run.py:1101-1108); Makefile `example-08` target carries no `--live` and no live variant exists (Makefile:75-78); data sent is synthetic-only. See Accepted Risks | closed |
| T-12-07 | Information Disclosure | docs/demo-walkthrough.md includes | mitigate | All 10 `--8<--` include directives reference `examples/08-e2e-demo/*` paths only (demo-walkthrough.md:78, 84, 134, 181, 185, 197, 210, 258, 266, 286); grep for any non-example include path returns none — no whitepaper or `.planning` internals included | closed |
| T-12-SC | Tampering | package installs | accept | Zero installs this phase: `tech-stack.added: []` in all three SUMMARYs; Makefile diff adds only the `example-08` target/aggregate wiring, no dependency changes | closed |

---

## Accepted Risks

| Threat ID | Risk | Rationale | Accepted By |
|-----------|------|-----------|-------------|
| T-12-02 | Generated banking data could be mistaken for or collide with real PII | Data is fully synthetic by construction: every name, tax id, address, and amount is composed from scenario.yaml lexicons under a fixed seed; no real-world data source is read | Phase 12 plan 01 threat model |
| T-12-06 | `--live` sends the rendered prompt and detection outcome to an external LLM endpoint | Payload is synthetic-only; the branch is opt-in local (`--live` flag), never wired into `make examples`/`make ci`; nothing about model output is asserted or fed back into detection | Phase 12 plan 02 threat model |
| T-12-SC | Supply-chain tampering via new packages | No packages installed or added this phase | Phase 12 plan threat models |

---

## Threat Flags (from SUMMARYs)

- 12-03-SUMMARY declares **Threat Flags: None** (and affirms T-12-07 include discipline).
- 12-01 and 12-02 SUMMARYs contain no `## Threat Flags` section — treated as none declared; no new attack surface claimed by executors.

### Unregistered observations (WARNING, non-blocking)

1. **CREATE TABLE column-type interpolation** — generator.py:145-151 interpolates the artifact-supplied column `type` string into the CREATE TABLE statement unquoted (it is neither a value parameter nor passed through `sql_identifier`). This sits entirely inside the declared "self-authored artifact, no external input" trust boundary and cannot be reached by external data, but it is the one artifact-sourced string in the SQL surface that bypasses the centralized quoting helper. Recommend routing it through validation or the quoting helper if scenario.yaml ever becomes user-supplied input (e.g., Phase 14 "make your own demo" adoption path).

---

## Audit Trail

- Audit date: 2026-08-02
- Auditor: gsd-security-auditor (post-WR-01..WR-05 review-fix state, commits 1df8b69..d281efa)
- Files examined: examples/08-e2e-demo/generator.py, examples/08-e2e-demo/run.py, examples/08-e2e-demo/artifacts/skills.yaml, examples/08-e2e-demo/artifacts/controlplane.yaml, docs/demo-walkthrough.md, Makefile, all three phase PLANs and SUMMARYs
- Implementation files modified: none
