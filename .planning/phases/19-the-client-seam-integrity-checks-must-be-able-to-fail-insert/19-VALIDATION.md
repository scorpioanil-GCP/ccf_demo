---
phase: 19
slug: the-client-seam-integrity-checks-must-be-able-to-fail
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-19
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
>
> **Source:** `19-RESEARCH.md` § *Validation Architecture* (properties 1–5,
> requirements→test map, coverage claim). That section is authoritative; this
> file is the execution-facing contract derived from it.
>
> **This phase is unusual: its entire deliverable is that a check *can fail*.**
> Every property below is therefore stated as a sabotage plus the observation
> that proves the sabotage was caught — per `CLNT-12` / `D-22`, the named
> sabotage control is written in the same plan as the assertion, never deferred.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (config `pyproject.toml:141-152`; markers include `conformance`, `crossproc`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/client -q` |
| **Wave-merge command** | `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/client tests/mcp tests/crossproc tests/http_api -q` |
| **Full suite command** | `make ci-core` (= `lint typecheck test gate-tools`) |
| **Phase gate** | `make ci` exit 0 (`ci-core` + `examples` + `docs-strict` + `gate-tools`) |
| **Estimated runtime** | quick ~seconds (374 tests) · full suite minutes |

> **Never invoke bare `python`** — it does not exist on this host. Always
> `.venv/bin/python` with `PYTHONPATH=src:runtime` (`Makefile:10-11`).

**Baseline to reconcile against:** 4027 collected / 3909 passed / 118 skipped /
0 failed at HEAD `192c79d`. Per the `D-GATE-18` / `D-GATE-18.1` discipline,
**every test-count increment at the gate must be traceable to a named finding
or a named new property.**

---

## Sampling Rate

- **After every task commit:** `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/client -q`
- **After every plan wave:** the wave-merge command **and** `make lint`
- **Before `/gsd:verify-work`:** `make ci-core` green
- **Phase gate:** `make ci` exit 0, test delta reconciled against the 4027 baseline
- **Max feedback latency:** < 60s at task level

---

## Per-Property Verification Map

The properties are the phase. Task IDs are assigned by the planner; this table
is the contract each task's `<acceptance_criteria>` must discharge.

| # | Property | Sabotage (named control) | Observation that proves it | Single-transport? |
|---|----------|--------------------------|----------------------------|-------------------|
| **P1** | A transport that answered a **different question** is detected | Hostile in-repo adapter subclassing the *shipped* adapter: asks the real door question **B** while the client asked **A**, returns the door's bytes **unmodified** | `pytest.raises(TransportError, match="different question")` **and no `Result` produced at all** — not a refusal. Exact `D-10` type, not the `BindingError` subclass | ✅ one client, one adapter, one deployment |
| **P2** | A **vessel altered in transit** — bytes not matching the producer-claimed address — is detected | (a) hostile adapter edits vessel text in the returned bytes, leaves the claimed address alone; (b) codec-level: `decode_outcome(tampered_bytes, sent=…)`, tamper = post-encoding byte edit inside `product_json` | `pytest.raises(TransportError, match="content address")`. Assert on the message, **not** a digest value | ✅ (a) one client one adapter; (b) no transport at all — pure function over bytes |
| **P3** | The seam **cannot be bypassed by the next adapter** (`C-12`) | Generic byte-corrupting decorator in `suite.py` applied to **every** registered `AdapterSubject` — generic only because `C-05` made the seam bytes; an adapter author writes nothing and cannot opt out | Per subject: `TransportError` with the discriminating message, **and** the honest subject not raising | ✅ legs iterate subjects and assert **per subject**; no cross-subject comparison |
| **P4** | The guard preventing **false** failures is what is preventing them | Construct an outcome whose echo carries a parameter the guard refuses (e.g. `Decimal` rendered as text); show shipped `check_outcome` raises on a wire that **worked** | `TransportError` `match="different question"` on a *healthy* exchange — the exact false-positive `wire.py:147-162` says the guard exists to prevent | ✅ pure codec-level |
| **P5** | `C-02`'s **as-asked** temporal echo (regression — already pinned) | — none new — | `suite.assert_decision_instant_is_auditable` asserts `served.temporal_boundary is None` for `as_of=None`, over **both** real transports. **Currently green; must stay green.** It is the mechanical tripwire on the §2.3 design choice | ✅ asserted per subject |

### Mandatory guards on the above

| Guard | Applies to | Why it exists |
|-------|-----------|---------------|
| **Vacuity guard** | P1, P2, P3 | The same subject, untampered, on the same question, must **not** raise. Without it, *"everything raises"* passes every leg. |
| **Discrimination guard** | P2 | Tampered bytes must stay **well-formed and contract-valid**, so the failure is attributable to the address check — not the parser (`codec.py:296`) or the contract check (`codec.py:254`). Appending whitespace *inside* the vessel's JSON text achieves this. |
| **Control on the control** | P1, P2 | Hand the assertion an **honest** adapter and assert the assertion fails — the `test_the_suite_fires.py` discipline. |
| **Neutrality guard** | P3 | `test_the_suite_fires.py:933-953` must stay green: no new leg may contain a `SCHEME_REGISTRY` key, and (per no-hardcoding over `tests/`) no spelled product id or parameter name. |
| **Ordering guard** | P1 covering refusals | `check_outcome:236` runs the echo comparison **before** the `product_json is None` branch at `:245`, so `C-04`'s "one comparison covers served and refused" holds *by construction*. **Verify this ordering survives the refactor** — moving the check below the branch silently uncovers the refusal half. |

---

## Decision → Test Map

| Decision | Behavior | Test type | Automated command | Exists? |
|---|---|---|---|---|
| `C-01`,`C-03`,`C-04` | producer mints the echo; total `WireRequest` equality; one comparison covers served **and** refused | unit | `pytest tests/client/test_codec.py -q` | ⚠️ partial — refused-half echo leg is new |
| `C-02` | `as_of=None` echoes `None` | conformance | `pytest tests/client/conformance -q -k decision_instant` | ✅ exists — **must stay green** |
| `C-05`,`C-08` | seam returns bytes; `decode_outcome` on the shipped path | unit + type | `pytest tests/client -q`; `make typecheck` | ❌ the retype itself |
| `C-06` | `_decode` has no transcoding step | source assertion | AST/source gate that the adapter builds no outcome object | ❌ new (see Open Ruling 3) |
| `C-07` | in-process is a degenerate wire in **both** directions | unit | `pytest tests/client/test_inprocess_adapter.py -q` | ⚠️ `:295-336` asserts the answer half; question half is new |
| `C-09` | HTTP publishes the echo as an `X-CCF-*` sibling; absent when no question was posed | unit | `pytest tests/http_api/test_content_address_header.py tests/http_api/test_routes.py -q` | ❌ new |
| `C-10` | the claim in prose matches what the code detects | docs/lint | `make lint` (citations) + human read at close | ❌ new prose |
| `C-11` | single-transport falsification | conformance control | `pytest tests/client/conformance -q -k crossed` | ❌ new — **one deleted line from existing** (`test_the_mcp_binding_fires.py:57-70`) |
| `C-12` | tamper legs on every registered adapter | conformance | `make conformance` | ❌ new |
| `CLNT-06` | one `Result` construction site survives | AST gate | `pytest tests/client/test_surface.py -q` | ✅ exists |
| `CLNT-14` | `consume.py` purity + budget | AST gate | `make ci` examples job | ✅ exists — **must stay green** |

---

## Wave 0 Requirements

Existing infrastructure covers all phase properties. pytest, the conformance
suite (`tests/client/conformance/suite.py`), the suite's own meta-test
(`test_the_suite_fires.py`), and the AST-gate pattern
(`test_surface.py::count_result_construction_sites`) are all present and green.

**No framework install, no new fixtures directory.** What is new is legs and
controls inside existing files, plus the hostile-adapter controls.

---

## Manual-Only Verifications

| Behavior | Decision | Why Manual | Test Instructions |
|----------|----------|------------|-------------------|
| The narrower true claim in prose actually matches what the code detects | `C-10` | No lint can judge whether an English sentence overstates a detection capability. The citation lint proves the *reference* resolves, not that the *claim* is true. | At close, read `codec.py`'s docstring, `WireOutcome`'s attribute docs, and every changed doc/README/release-note line against P1+P2's actual coverage. Confirm nothing claims adversarial tamper detection (`C-10` puts signing out of scope) and nothing restates the false "the producing deployment answers against its own clock" sentence (`client.py:139-141`) unless Open Ruling 1 makes it true. |

---

## Coverage Claim — Stated Precisely

| Axis | Covered |
|---|---|
| **Transports** | `inprocess` **and** `mcp+stdio` — both as conformance subjects (generic legs) and as single-transport controls. **HTTP has no client adapter**, so the `C-09` echo header is verified **producer-side only**; state that limit rather than implying client-side coverage. |
| **Door types** | Served **and** refused, by one comparison (`C-04`), covered *by construction* via the ordering guard above. |
| **`WireRequest` equality axes** | All three — `product_id`, `parameters`, `temporal_boundary` — by total model equality (`C-03`). No projection, no field selection. |
| **`temporal_boundary`** | `None` stays `None` (`C-02`), pinned by an existing green conformance leg; aware instants round-trip across offsets and microseconds (verified, RESEARCH §6). |
| **`parameters`** | Every admissible type round-trips equal (19-case probe, RESEARCH §6); every inadmissible type is refused at construction, so no admissible question can produce a false failure. |
| **Not covered, and said so** | An adversary with envelope write access (`C-10` — signing out of scope, **no signature member reserved on the wire**); two *identical* in-flight questions crossing (accepted knowingly at discussion Q1); a producer that consistently mis-canonicalizes (RESEARCH §5.3); `A5` stdio-auth impersonation (carried unclosed from Phase 18). |

---

## Open Rulings Carried Into Planning

These are recorded here because they change what gets tested. See
`19-RESEARCH.md` § *Conflicts With Locked Decisions* and § *Open Questions*.

1. **Does the clock read move to the door?** Both adapters resolve
   `as_of=None → now(UTC)` client-side today, so `ProductClient.ask`'s docstring
   promise is false on both transports. `C-07`'s encoded-request design makes
   moving it nearly free — but `C-13` says stay narrow. **User ruling required.**
2. **Does `PRODUCT_REQUEST_TOOL` gain a required argument** (a wire-compat break
   for non-SDK consumers), ruled in the same `D-IMPL` entry as the out-of-tree
   adapter break?
3. **Does the phase add an AST gate** proving no adapter constructs the outcome
   (`C-06`'s "no transcoding step")? Narrow, mirrors `CLNT-06`'s existing
   pattern; a type change binds `mypy` over `src`/`runtime` only and is
   invisible to an out-of-tree adapter.

---

## Validation Sign-Off

- [ ] Every property P1–P5 has a named sabotage control **in the same plan as its assertion** (`CLNT-12`, `D-22`)
- [ ] Every sabotage leg carries its vacuity guard
- [ ] P2 carries its discrimination guard
- [ ] P1/P2 carry a control-on-the-control
- [ ] P3 carries the neutrality guard (`test_the_suite_fires.py` stays green)
- [ ] The ordering guard is asserted, not assumed
- [ ] **No leg passes because "everything raises"**
- [ ] **No proof requires two subjects** — the phase's success sentence is single-transport
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] No watch-mode flags
- [ ] `make ci` exit 0 with the test delta reconciled against the 4027 baseline
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
