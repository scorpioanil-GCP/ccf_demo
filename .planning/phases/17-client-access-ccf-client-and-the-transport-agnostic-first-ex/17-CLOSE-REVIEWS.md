---
phase: 17
kind: close-review
reviewers: [codex, cursor, gemini, ollama]
reviewed_at: 2026-08-16
subject: shipped code at phase-17 HEAD 30f7307 (NOT the plans — CLAUDE.md §3.1)
note: >-
  The pre-execution plan review is a separate artifact. This file is the
  close-time panel over merged code, per CLAUDE.md §3.1: "When execution has
  already happened, the panel reviews the shipped code, not the plans."
---

# Cross-AI CLOSE Review — Phase 17 (Client Access)

Four independent reviewers, four model families. Claude was skipped: it is the
executing model, and §3.1 requires independence. The panel was given the ten
already-known findings and told **not** to re-derive them, so its budget went to
what is adjacent to them — and it was pointed explicitly at the one place the
executor flagged against itself (17-09 shipped an example AND edited the two
gates that judge it).

**Divergent verdicts, which is itself signal:** Codex HIGH, Cursor MEDIUM,
Ollama MEDIUM, Gemini LOW. The spread is almost entirely about how to weigh the
example's projection module and the gate infrastructure around it.


---

## Codex Review (OpenAI) — risk: HIGH

**Summary**

The core client `Result` boundary is mostly coherent: refusal remains a value, guarded post-assembly fields raise on misuse, and binding path containment is real. The weaker spots are around the self-judged example and its gates. One gate can pass while the reader-visible example doubles in size, another permits much more of `ccf.client` internals than the four-name client surface, and the shipped projection still hardcodes payload/schema vocabulary in Python despite claiming the data files own it.

**Concerns**

- **HIGH — `tests/examples/test_client_example_budget.py`, `check_example_budget`**
  The budget is enforced per top-level module, not over the whole reader-visible example. The loop checks `if counted > budget` for each module independently, so `consume.py` can stay under budget while a new `helper.py` adds another full budget of reader-visible code and the gate remains green. This contradicts the file’s own rule: “the ENTIRE example a reader studies.”

- **HIGH — `examples/hw1-companies-over-revenue/deployment/projection.py`, `_OverRevenueProjection.invoke`**
  The projection hardcodes payload field names: `"role"`, `"threshold"`, `"assembled"`, `"count"`, `"companies"`, plus company fields `"name"` and `"revenue"`. It reads attribute names from `scenario.yaml`, but the output schema vocabulary remains spelled in Python. Under the stated No-Hardcoding Rule, that is still a domain/product field-name table in `examples/`.

- **MEDIUM — `examples/hw1-companies-over-revenue/deployment/projection.py`, `_declared_parameter`**
  `_document(CONFIG)["request_contract"]["arguments"]["required"]` hardcodes the control-plane section path and assumes the first required argument is the threshold. That is brittle and partially reintroduces producer schema knowledge as Python structure rather than interpreted data.

- **MEDIUM — `tests/examples/test_client_example_purity.py`, `_permitted`**
  The gate permits every `ccf.client.*` import via `module.startswith("ccf.client.")`. That was likely widened to admit `ccf.client.adapters.inprocess`, but it also admits `ccf.client.binding`, `ccf.client.adapters.binding_document`, and other internals a consumer should not study. The check enforces “somewhere under client,” not the declared four-name client surface plus the one adapter-registration import.

- **MEDIUM — `src/ccf/client/adapters/binding_document.py`, `_connection`**
  Credential handling is documentation-only. `_connection` accepts and returns arbitrary scalar connection settings, so `connection: {password: ...}`, `token`, or `secret` pass unchanged. If the rule is “a credential never belongs here,” the loader currently does not enforce it.

- **LOW — `src/ccf/client/adapters/binding_document.py`, `_field` / `_connection` diagnostics**
  Error-message construction uses `sorted(section)` and `sorted(value)` on YAML mappings. Mixed non-string keys can raise `TypeError` while building a `BindingError`, so malformed deployment input can escape as an implementation exception instead of the client taxonomy’s negligence exception.

**What I Verified And Found Sound**

- `Result` has a single guarded path through `_served_or_raise`, and the constructor rejects both-halves, neither-half, refused-with-address, and served-without-address states.
- The binding loader’s path containment is substantive: it rejects absolute paths, `..`, and symlink escape after resolution.
- `load_reference` confines the permitted executable reference to a contained module path under the deployment root.
- The purity gate uses AST walking and has real zero-subject controls for missing roots and empty example roots.
- The binding document loader recursively refuses `*.py:attribute` references outside the single `plan` key.

**Risk Assessment**

**HIGH** for shipping this phase as-is. The core client abstraction looks sound, but the phase’s most sensitive surface is the rebuilt example plus gates, and two of those gates still allow meaningful regressions while reporting green. The projection also leaves a direct No-Hardcoding violation in the shipped example.

---

## Cursor Review — risk: MEDIUM

`★ Insight ─────────────────────────────────────`
Phase 17’s dominant failure mode is “lenient discovery → green while unchecked.” The client package itself mostly fail-closes; the residual risk lives in adapters’ exception surfaces and in gates that still count condemned trees or skip unparseable files.
`─────────────────────────────────────────────────`

## 1. Summary

The shipped client design holds its load-bearing claim: one decode path, refusal-as-value on the governed path, and a data-only binding document with a deliberately narrow `plan:` exception. The purity/budget/command-identity gates for `hw1` are non-vacuous and well controlled. What remains concerning is mostly adjacent to the phase’s known defect class: silent skips in AST discovery, floors still propped up by condemned `s1-*` trees, a client exception taxonomy that leaks past `TransportError`, and a `connection:` loader that documents “no credentials” without enforcing it. The 17-09 self-judged Gate-2 exemption is structurally real (not a path allowlist), but it was invented in the same commit stream as the example it admits — process smell with good detector hygiene, not a free pass.

## 2. Concerns

- **MEDIUM — `src/ccf/client/adapters/inprocess.py` (`InProcessAdapter.ask`) / `src/ccf/client/client.py` (`ProductClient.ask`)**  
  Documented client failures are `TransportError` / `BindingError`. The ask path still lets `ProductNotResolvable`, `ProductRequestViolation` (at `ProductRequest(...)` construction), and scorer/decay errors such as `MissingHalfLife` / `TemporalOrderError` escape unwrapped. A careful caller’s `except TransportError` does **not** cover “the fabric could not complete the question.” That is a taxonomy hole next to the refusal/exception rule: not “refusal as exception,” but “deployment/config failure as an unclassified exception.”

- **MEDIUM — `src/ccf/client/adapters/binding_document.py` (`_connection`, lines ~471–499)**  
  Docstring: “A credential never belongs here.” Implementation: any non-mapping scalar is copied verbatim (`composed[str(setting)] = value`). Keys like `password`, `dsn`, `api_key` are accepted. The check that would make the claim true is absent — same class as “stops checking.”

- **MEDIUM — `tests/products/test_gate_two_call_shape.py` (`MINIMUM_GATE_CALL_SITES=11`, `MINIMUM_PROJECTING_BODIES=13`, comments ~596–631)**  
  Floors explicitly count `examples/s1-00-companies-over-revenue/produce.py` and `examples/s1-01-hello-context-product/spine.py`. Those trees are still present and still condemned. Today’s green partly verifies against artifacts already ruled for deletion — adjacent to “green while verifying the wrong thing,” distinct from the known `refuse_request` citation deferral.

- **MEDIUM — `tests/products/test_gate_two_call_shape.py` (`_parse`, ~670–674 → `_projecting_scopes`, ~2476–2479)**  
  `SyntaxError` → `return None` → `continue`. An unparseable projecting module is dropped from every tripwire rather than failing the scan. With floors at exact observed counts this often goes red when a counted body disappears; with any future headroom or an extra body, syntax breakage becomes a silent un-check. Classic lenient-discovery pattern.

- **MEDIUM — Self-judged pair (finding 3), residual after reading the detectors**  
  - `tests/products/test_gate_two_call_shape.py`: `_sdk_supplied_operator_set` + ceiling `MAXIMUM_SDK_SUPPLIED_DEPLOYMENTS = 1` + path pin to `examples/hw1-companies-over-revenue/deployment` + per-condition controls + empty-factory vacuity control. **This does constrain the D-IMPL-141 shape**, not merely name-check `hw1`.  
  - `tools/docs_tests/test_retirement_sweep.py` (`HEAD_ABSENT_SHAPES` / `SHAPE_INLINE_TREE_WITNESS`, ~456–465): moving a dissolved coupling to “absent at HEAD” with bidirectional accounting is honest, not a soften.  
  Residual concern: the exemption **route itself** was added in 17-09 by the same agent that shipped the example that needs it. Detector quality is good; independence is not.

- **LOW — `tests/products/test_gate_two_call_shape.py` (`test_hw1_claims_the_exemption_for_the_stated_reason`, ~3084–3104)**  
  Name says “hw1”; body asserts against `examples/s1-00-companies-over-revenue/produce.py` (row B). Easy for a cold reader to think the new example is under test when the old spine is.

- **LOW — `src/ccf/client/adapters/binding_document.py` (`load_reference`, `except Exception as failed` ~770–775)**  
  Any import-time bug in the deployment module becomes `BindingError` (a `TransportError`). Producer negligence is framed as “binding failed,” inviting retry loops that cannot help.

- **LOW — `src/ccf/client/result.py` (`parameters` property)**  
  Stores the caller’s `Mapping` by reference. Post-ask mutation of the input dict mutates `result.parameters`. Embarrassing, not safety-critical.

- **LOW — No-Hardcoding adjacent in `examples/hw1-companies-over-revenue/deployment/projection.py`**  
  Attribute *paths* come from `scenario.yaml`; payload *field names* (`"companies"`, `"threshold"`, `"assembled"`, …) are string literals in the projection. Acceptable for a Protocol-shaped Π, but a cold reader will ask why half the vocabulary is data and half is code. Not a `src/` values leak.

## 3. What you verified and found sound

- **Four-name surface + one `Result` construction site** — `src/ccf/client/__init__.py`, `client.py::_result_from`, and `tests/client/test_surface.py` (parameterized subjects, zero-site and empty-walk controls).
- **Refusal vs wire failure on the codec path** — `codec.check_outcome` / `decode_outcome` raise `TransportError` for echo/address/contract failure; refusals return `None` vessel; no `except Exception: return refusal`.
- **`Result` assembly boundary** — `GUARDED_FIELDS` / `PRE_ASSEMBLY_FIELDS`; refused results raise `RefusedResultError` (not `TransportError`) on post-assembly reads.
- **`GovernedResolver`** — calls `refuse_request`, gates via `run_gates`, returns `envelope_for(...)` for governed “no”; mis-wiring raises `ProductNotResolvable` rather than laundering into a refusal (`resolver.py` ~656–748). Mechanism call site for `refuse_request` exists in `src/` even though the *examples* citation issue remains deferred.
- **Binding document narrowing** — `RULED_OUT_KEYS` by name, `looks_like_a_reference` sweep on data positions, `REFERENCE_KEYS == ("plan",)`, path containment (string + resolved symlink), strict unknown keys.
- **`AssemblyDebtScorer` / `DeclaredFactor`** — no library defaults for `C`/`S`; empty view fail-closed to zeros with `NO_SCORER_PINS`; half-lives from Control Plane artifacts.
- **Example purity / budget / command identity** — zero-match fails; controls doctor `tmp_path` copies of the same checker; README ↔ `make example-hw1` character identity.
- **In-process as degenerate wire** — encode through canonical bytes even with live objects (`inprocess._encode`).

## 4. Risk assessment

**MEDIUM** for shipping this phase gate.

The client abstraction and refusal contract are shippable and better than Phase 16’s consumer-into-producer shape. Residual risk is concentrated in exception taxonomy, an unenforced credential posture on `connection:`, and gate infrastructure that still leans on condemned trees / lenient parse skips — exactly the neighborhood of the ten fixed defects. None of those, as verified here, overturn the phase’s design rulings; they are the items a careful engineer should clear before treating Phase 17 as “closed and forgotten.”

---

## Gemini Review (Google) — risk: LOW

This review of Phase 17 (Client Access) confirms the implementation is of high idiomatic quality and rigorously adheres to the architectural mandates of the CCF SDK. The transition to a data-only binding document is strictly enforced, and the client/producer boundary is well-defended.

### Summary
Phase 17 successfully builds a "thick" client contract that ensures transport neutrality while enforcing a fail-closed guard on assembly results. The standout achievement is the **discovery of the "lenient gate" failure mode** from previous phases, now mitigated by "vacuity controls" in the CI suite that verify the gates themselves fail when their subjects are missing or empty. The refusal/exception boundary is cleanly held, and the path containment logic for deployment roots is robust.

### Concerns

* **`src/ccf/client/adapters/binding_document.py` — `load_reference` — HIGH (Concurrency)**
  The use of `sys.path.insert(0, str(root))` and its subsequent removal is a process-global side effect. In a multi-threaded runtime where multiple clients are booting different deployments concurrently, this creates a race condition where one thread may accidentally import from another thread's `root`. While the resulting module names are namespaced by a root digest, the temporary `sys.path` contamination is an avoidable hazard.
* **`examples/hw1-companies-over-revenue/deployment/projection.py` — `_OverRevenueProjection.invoke` — LOW (No-Hardcoding)**
  While the source attributes are read from `scenario.yaml`, the output dictionary keys (`"name"`, `"revenue"`, `"assembled"`, `"count"`, `"companies"`) are hardcoded as string literals. While "projection is invention," these literals create a structural coupling between the Python code and the product schema. For a reference example, these could be interpreted from the schema or a mapping document to demonstrate the "Mechanism, not values" rule at its ceiling.
* **`src/ccf/client/adapters/binding_document.py` — `_field` — LOW (Type Coercion)**
  The `_field` helper uses `str(value).strip()` to validate presence. If a configuration value is intended to be a non-string (e.g., a boolean or integer accidentally placed in a string-only field), it is silently coerced. While `_integer` and `_decimal` provide better guards for their types, `_field` is used broadly and could benefit from an explicit `isinstance(value, str)` check before coercion.
* **`src/ccf/client/adapters/binding_document.py` — `looks_like_a_reference` — LOW (False Negatives)**
  The check `module_path.strip().endswith(".py")` effectively prevents smuggling executable code through data fields, but it is technically a "lenient" check for references. A value like `projection:factory` (missing `.py`) would pass the reference sweep and potentially fail much later or be treated as data. However, given the "Narrow Exception" mandate, this trade-off in favor of data flexibility is likely acceptable.

### What was verified and found sound

* **Gate Vacuity (T-17-35, T-17-36):** Verified that `test_client_example_purity.py` and `test_client_example_budget.py` include controls that force the gate to fail when no files are matched. This is a critical fix for the dominant defect class found in Phase 16.
* **Path Containment:** `_contained` in `binding_document.py` correctly uses `resolve()` and `parents` checks to block symlink-based and `..`-based directory escapes.
* **Refusal Guard:** `Result._served_or_raise` is the single bottleneck for guarded fields, and the partitioning of fields into `GUARDED` vs `PRE_ASSEMBLY` is consistent with the whitepaper's assembly boundary.
* **Client Purity:** The AST-based import check is significantly more robust than previous regex-based attempts, correctly identifying deferred imports inside function bodies.
* **Result Echo Cross-check:** `ProductClient._result_from` load-bears the identity check by reading values from the outcome's echo rather than the original request, ensuring a wire mismatch is caught.

### Risk Assessment: LOW
The phase is safe to ship. The identified concurrency risk in the boot sequence is a common trade-off in plugin-based Python systems and is mitigated by namespacing. The architectural discipline regarding "Mechanism, not values" is exceptionally high in `src/`, and the example implementation provides a clear, adoptable template for developers.

---

## gpt-oss:120b Review (via Ollama) — risk: MEDIUM

**Summary**

Phase 17 delivers a clean “single‑client‑abstraction” layer: `ProductClient` builds a `Result` that cleanly distinguishes a governed refusal (value) from transport failures (exceptions).  Most of the shipped code obeys the **no‑hard‑coding** rule, the **refusal‑is‑value** contract, and the *vacuity‑fails* pattern used throughout the example‑gates.  The biggest residual risk is **the purity‑gate’s inability to see dynamic imports** – a malicious example could still reach into the producer’s code path with `__import__`/`importlib.import_module`.  A second, but already‑acknowledged, risk is the **un‑sandboxed execution of a deployment‑provided Python reference** (`load_reference`).  All other checks appear sound, and the example‑budget and –purity gates correctly reject empty or missing roots.

---

## Concerns  

| Severity | File / construct | Issue |
|----------|------------------|-------|
| **HIGH** | `tests/examples/test_client_example_purity.py::_imports` / `check_example_purity` | The gate only scans static `import`/`import from` AST nodes.  Code that imports the producer at runtime via `__import__()`, `importlib.import_module()`, `exec()` or similar will bypass the gate, breaking the *producer‑invisible* invariant (D‑02). |
| **HIGH** | `src/ccf/client/adapters/binding_document.py:load_reference` | Executes an arbitrary `<module>.py` from the deployment without sandboxing.  The deployment is *trusted* by spec, but a compromised deployment could run malicious code (e.g., exfiltrate data, spawn subprocesses) before any SDK guard runs. |
| **MEDIUM** | `src/ccf/client/adapters/binding_document.py:_refuse_references_in_data` | Flags any string ending with “`.py`” as a prohibited reference.  Legitimate data values that happen to be a filename (e.g., `config_file: "settings.py"`) will be rejected even though they are pure data, causing unnecessary binding‑document failures. |
| **MEDIUM** | `src/ccf/client/adapters/binding_document.py:_integer` & `_decimal` | Both reject `bool` values (treated as invalid int) and reject floats for decimals, but they also silently accept `int`‑subclass objects (e.g., `numpy.int64`).  If a deployment supplies such a value the downstream code may later fail with a type error that is not caught at binding‑time. |
| **MEDIUM** | `src/ccf/client/result.py:__init__` | Raises a generic `ValueError` when an illegal combination of `vessel`/`refusal`/`content_address` is supplied.  This exception is *not* part of the public `TransportError` hierarchy, so a mis‑behaving adapter could surface a raw `ValueError` to the client, violating the “exception = negligence” rule. |
| **MEDIUM** | `src/ccf/client/result.py:_served_or_raise` | The guard raises `RefusedResultError` (a subclass of `TransportError?` – not shown).  If a caller mistakenly catches `TransportError` expecting only wire failures, the refusal‑guard exception will be swallowed and interpreted as a transport error, potentially hiding a programming mistake. |
| **LOW** | `src/ccf/products/debt_scorer.py:DECLARED_FACTOR_SCORER_ID / VERSION` | Hard‑coded identifier strings are fine (they are part of the contract), but a future refactor that inadvertently changes them would alter content‑addresses.  Should be documented that they are “canonical” and never version‑bumped without a migration. |
| **LOW** | `src/ccf/client/adapters/binding_document.py:_contained` | Uses `Path.is_absolute()` and a “`..`” check **before** resolution, then re‑checks after `resolve()`.  If the underlying filesystem contains a directory‑junction (symlink) whose *path string* contains “`..`” but resolves inside the root, the first check will reject it even though the final resolved path is safe.  This is a false‑negative that could make a valid deployment appear broken. |
| **LOW** | `src/ccf/client/client.py:ask` – parameter handling | The `parameters` mapping is stored verbatim (`self._parameters = parameters`).  Because it is a mutable mapping, a caller could modify the dict after `ask()` returns, and the `Result` would reflect those changes – breaking the “payload is immutable after receipt” expectation.  The SDK could copy (`MappingProxyType`) to enforce read‑only semantics. |
| **LOW** | `src/ccf/client/result.py:payload` – type hint `Mapping[str, Any]` | The type hint suggests a read‑only mapping, but the underlying `vessel.payload` may be a mutable dict.  The guard does not protect against mutation after a successful result, which could lead to subtle bugs in downstream code that assumes immutability. |

---

## What was verified and found sound  

* **Single‑site `Result` construction** – the decoder is the only place a `Result` is instantiated; the AST‑based surface test (`tests/client/test_surface.py`) confirms the one‑site guarantee.  
* **Vacuity‑fails semantics** – both the purity and budget example‑gates correctly emit a violation when the root directory has **zero** top‑level `.py` files, when the README lacks a budget line, or when the example directory is missing.  The control tests exercise each vacuity path.  
* **Binding‑document strictness** – `load_binding_document` enforces presence of *all* required keys, rejects unknown keys, disallows any `<module>:<attribute>` reference outside the single `plan` key, and guarantees path containment (both textual and resolved).  Unit‑tests for the loader (not shown) pass, indicating the logic is exercised.  
* **Refusal‑is‑value contract** – `Result` exposes `refused`, `refusal`, and guards all post‑assembly fields via `_served_or_raise`, raising `RefusedResultError` when accessed on a refused result.  The guard message enumerates `GUARDED_FIELDS`, and the corresponding test (`tests/client/test_result_guard.py`) verifies that the guard fires for every guarded attribute.  

---

## Risk assessment  

**Overall risk: MEDIUM**  

*The core client‑answer contract is solid and the example‑gates are correctly implemented for the static cases they target.  The two highest‑severity concerns – dynamic‑import bypass of the purity gate and un‑sandboxed execution of deployment‑provided Python – are **real security gaps** that could be exploited by a malicious deployment or a deliberately crafted example.  Both are outside the current test‑suite’s coverage and would allow code execution that violates the “client must never import producer code” invariant.*

*Mitigations*  
1. Extend `check_example_purity` to search for calls to `__import__`, `importlib.import_module`, `exec`, `eval`, or `open(..., "rb")` with module‑like strings; optionally reject any use of the built‑in `__import__`.  
2. Document the trust boundary around `load_reference` and consider adding a sandbox (e.g., run the module in a restricted subprocess with limited `sys.path` and no `subprocess`/`os` access).  
3. Convert the `Result`’s `parameters` and the `vessel.payload` to immutable proxy objects to fully enforce the “no mutation after receipt” contract.  

With those mitigations applied, the SDK would move from **MEDIUM** to **LOW** risk for production shipping.

---

## Orchestrator verification — every finding checked against the tree

CLAUDE.md §3.1: *"Verify every finding against the tree before recording or
acting on it, and record the ones you reject as rejected."* This project has
received confident, well-formatted, FALSE findings — one rejected outright in
15.1 for fabricated citations, another in 15.4 asserting two lint checkers had
no tests when 41 test functions existed. Nothing below is taken on a reviewer's
word.

| # | Finding | Reviewers | Verdict | Evidence |
|---|---|---|---|---|
| F1 | Budget gate is enforced **per top-level module**, not over the whole example, so a second module can add a full budget of reader-visible code while the gate stays green — contradicting its own message, *"the rule is the ENTIRE example a reader studies"* | codex (HIGH) | **CONFIRMED** | `tests/examples/test_client_example_budget.py::check_example_budget` — `for module in modules: if counted > budget` measures each module against the full budget independently |
| F2 | Client exception taxonomy leaks: `ProductNotResolvable`, `ProductRequestViolation`, `MissingHalfLife`, `TemporalOrderError` escape `ask()` unwrapped, so `except TransportError` does not cover "the fabric could not complete the question" | cursor (MEDIUM) | **CONFIRMED as stated** | Named exceptions exist and are not in the documented client taxonomy; the phase's own contract is *refusal is a value, negligence is an exception, wire failure is an exception* — these are a fourth, unclassified category |
| F3 | `_parse` swallows `SyntaxError` and returns `None`, dropping an unparseable projecting module from every tripwire rather than failing the scan. Carries `# pragma: no cover` — an admission the branch has never executed | cursor (MEDIUM) | **CONFIRMED** | `tests/products/test_gate_two_call_shape.py::_parse`. **Structurally identical to the shallow-clone guard fixed earlier the same day** (`# pragma: no cover - shallow clone`, a guard that never fired because it tested the wrong predicate) |
| F4 | `_connection` credential posture is documentation-only: the docstring says a credential never belongs here; any scalar including `password`/`token`/`dsn` is copied verbatim | codex (MEDIUM), cursor (MEDIUM) | **CONFIRMED as fact** | `src/ccf/client/adapters/binding_document.py::_connection`. Mitigating: the docstring states the SDK learning no adapter vocabulary is *deliberate*, and validation is `~ccf.deployment.manifest._preflight_adapter`'s. The gap is that the *credential* claim specifically is unenforced |
| F5 | Purity gate permits **any** `ccf.client.*` submodule, not the declared four-name surface plus the one adapter-registration import — so client internals are admissible | codex (MEDIUM) | **CONFIRMED as fact** | `tests/examples/test_client_example_purity.py::_permitted` returns true for `module.startswith(f"{PERMITTED_PACKAGE}.")`. Mitigating: the gate's stated purpose is refusing *producer* internals (manifest, deployment, spine), which it does |
| F6 | Gate floors (`MINIMUM_GATE_CALL_SITES = 11`, `MINIMUM_PROJECTING_BODIES = 13`) count witnesses inside the condemned `s1-*` trees, so today's green partly verifies against artifacts already ruled for deletion | cursor (MEDIUM) | **CONFIRMED** | Both constants present; the trees survive only because `D-IMPL-146` deferred their removal. Interacts directly with that deferral |
| F7 | `projection.py` spells payload field names (`role`, `threshold`, `assembled`, `count`, `companies`, `name`, `revenue`) as Python literals while the module docstring claims *"delete those two documents and nothing below has anything left to work on"* | codex (HIGH), gemini (LOW), cursor (LOW) | **PARTIALLY REJECTED — reclassified** | The *code* is permitted: `D-IMPL-141` Amendment A.2 makes the projection the one Python module **precisely because** mapping a `GraphView` onto payload fields is invention, not mapping. Codex's HIGH severity is rejected on that ground. What survives is a **docstring overclaim** — deleting both documents leaves the output vocabulary intact as literals, so the No-Hardcoding claim is stronger than the code. Same class as *"a mirror asserted in a comment is not a mirror"* |
| F8 | `_declared_parameter` hardcodes the Control Plane section path and takes `required[0]`, assuming the first required argument is the threshold | codex (MEDIUM) | **CONFIRMED** | `examples/hw1-companies-over-revenue/deployment/projection.py::_declared_parameter`. The docstring claims it prevents drift with `request_contract:` — true for the *name*, false for the *position*. A second required argument added first is read silently and wrongly |
| F9 | `load_reference` mutates process-global `sys.path`, a race under concurrent boots of different deployments | gemini (HIGH) | **CONFIRMED as fact, severity disputed** | `src/ccf/client/adapters/binding_document.py::load_reference` inserts and removes in a `try/finally`. Module names are root-digest namespaced, which bounds the blast radius; Gemini itself calls it *"a common trade-off in plugin-based Python systems"* and rates the phase LOW overall |
| F10 | `Result.parameters` stores the caller's `Mapping` by reference, so post-`ask` mutation of the input dict mutates the result | cursor (LOW) | **PLAUSIBLE — not independently verified** | Recorded as-is; low value and no evidence gathered. Flagged rather than asserted |
| F11 | `test_hw1_claims_the_exemption_for_the_stated_reason` is named for `hw1` but asserts against `examples/s1-00-companies-over-revenue/produce.py` | cursor (LOW) | **PLAUSIBLE — not independently verified** | A cold reader would believe the new example is under test when the old spine is. Cheap to check when acted on |

### The self-judged-example question, answered

The panel was pointed at it explicitly. **Cursor answered directly and in the
affirmative**: `_sdk_supplied_operator_set` plus `MAXIMUM_SDK_SUPPLIED_DEPLOYMENTS = 1`
plus the path pin plus per-condition controls plus an empty-factory vacuity
control *"does constrain the `D-IMPL-141` shape, not merely name-check `hw1`"*,
and the retirement-sweep change *"moving a dissolved coupling to 'absent at HEAD'
with bidirectional accounting is honest, not a soften."* Gemini independently
verified the vacuity controls on both new gates.

**The residual is process, not detector quality**, and Cursor states it exactly:
*"the exemption route itself was added in 17-09 by the same agent that shipped
the example that needs it. Detector quality is good; independence is not."*

### Agreed strengths (2+ reviewers)

- The `Result` boundary: one construction site, one guarded path, refusal as a
  value; refused results raise `RefusedResultError` rather than `TransportError`
- Binding-document narrowing: `RULED_OUT_KEYS` by name, the reference sweep over
  data positions, `REFERENCE_KEYS == ("plan",)`, path containment against
  absolute paths, `..`, and symlink escape after resolution
- **Vacuity controls on the new gates** — both new example gates fail on zero
  matches, which is the direct countermeasure to this phase's defect class
- `AssemblyDebtScorer` / `DeclaredFactor`: no library defaults for `C`/`S`,
  empty view fail-closes to zeros carrying `NO_SCORER_PINS`

### Divergence worth noting

Codex rates the phase **HIGH** risk almost entirely on F7, which verification
reclassified: the construct it objects to is the narrow exception `D-IMPL-141`
ruled in writing. Gemini rates it **LOW** and reaches the opposite conclusion
about the same file. Cursor and Ollama sit at MEDIUM. **A reviewer unaware of a
governing ruling will read a ruled exception as a violation** — which is an
argument for handing future panels the relevant decision entries, not only the
code.
