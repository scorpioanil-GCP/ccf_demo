---
phase: 17-client-access
reviewed: 2026-08-16
depth: deep
status: issues_found
files_reviewed: 24
files_reviewed_list:
  - src/ccf/client/__init__.py
  - src/ccf/client/result.py
  - src/ccf/client/client.py
  - src/ccf/client/wire.py
  - src/ccf/client/codec.py
  - src/ccf/client/errors.py
  - src/ccf/client/binding.py
  - src/ccf/client/adapters/__init__.py
  - src/ccf/client/adapters/binding_document.py
  - src/ccf/client/adapters/inprocess.py
  - src/ccf/products/resolver.py
  - src/ccf/products/debt_scorer.py
  - src/ccf/products/refusal.py
  - src/ccf/products/gates.py
  - src/ccf/deployment/config.py
  - src/ccf/deployment/manifest.py
  - src/ccf/contracts/canonical.py
  - runtime/ccf_runtime/http_api/dependencies.py
  - runtime/ccf_runtime/http_api/errors.py
  - examples/hw1-companies-over-revenue/consume.py
  - examples/hw1-companies-over-revenue/README.md
  - examples/hw1-companies-over-revenue/deployment/binding.yaml
  - examples/hw1-companies-over-revenue/deployment/projection.py
  - tests/products/test_gate_two_call_shape.py
  - tools/docs_tests/test_retirement_sweep.py
  - tests/client/conformance/suite.py
  - tests/examples/test_client_example_purity.py
  - tests/examples/test_client_example_budget.py
findings:
  blocker: 2
  critical: 2
  warning: 7
  info: 8
  total: 17
---

# Phase 17: Code Review Report

**Reviewed:** 2026-08-16
**Depth:** deep (cross-file; AST-gate behaviour probed by execution, not by reading)
**Status:** issues_found

## 1. Summary

The client abstraction itself is the strongest thing this phase shipped. `Result`'s
pre-assembly/post-assembly split is enforced structurally rather than documented,
`WireOutcome`'s two-state validator cannot be constructed around, `RefusalEnvelope`
dispatches on exact type rather than `isinstance` (the right call, for the right
recorded reason), and the conformance suite's `assert_decision_instant_is_auditable`
leg is genuinely non-vacuous with one subject. `make ci-core` is green and
`python -m tools.lints --all` is silent. I could not find a hole in the four-name
surface, the decode path, or the refusal taxonomy.

It is **not shippable as it stands**, for two reasons, neither of which is in the
client's logic. First, the phase added a projecting body and a `run_gates` call site
and did not raise the two floor constants that count them — so
`tests/products/test_gate_two_call_shape.py` now carries exactly the headroom its own
docstrings call "a licence", in the phase whose signature defect is a check that keeps
reporting green while measuring less. Second, `ProductClient.ask`'s documented
`as_of=None` contract ("the producing deployment answers against its own clock") and
the example README's "drop the flag and you get today's answer" are both false for the
only shipped transport: `InProcessAdapter` substitutes a literal instant from
`binding.yaml`, so the default path serves a product whose `expires_at` is five and a
half months in the past and prints it to the reader. Both are one-commit fixes.

On the question the executor flagged against itself: the new premise route is
**mostly genuine, with two specific soft spots** — see §3.

## 2. Findings

### BL-01 — Two floor constants gained headroom in this phase and were not re-raised (BLOCKING)

**File:** `tests/products/test_gate_two_call_shape.py::MINIMUM_GATE_CALL_SITES`,
`tests/products/test_gate_two_call_shape.py::MINIMUM_PROJECTING_BODIES`

**What is wrong.** Both constants are set below what the tree now contains, and both
of their own comments — plus `test_the_binder_scan_is_not_vacuous`'s docstring
("**Why the floor sits exactly at the observed count, with no headroom.** Headroom is
not slack, it is a licence") — assert that they sit exactly at the observed count.

| constant | value at HEAD | observed at HEAD |
| --- | --- | --- |
| `MINIMUM_GATE_CALL_SITES` | 11 | **12** |
| `MINIMUM_PROJECTING_BODIES` | 13 | **14** |
| `MINIMUM_RESOLVED_BINDER_SITES` | 12 | 12 (correct) |

The two new entries are both this phase's work:

- the 12th gate call site is `src/ccf/products/resolver.py::GovernedResolver.__call__`
  — `SCANNED_TREES` includes `"src"`, so the new reference composition is scanned. The
  constant's comment still reads *"eleven of them, counted from the tree: examples 00,
  01, 02, 03, `04-cross-process/producer_child.py`, 06, 07 and 08, plus …"* and names
  no `src/` site at all;
- the 14th projecting body is
  `examples/hw1-companies-over-revenue/deployment/projection.py::build_projection`. The
  constant's comment still reads *"Eleven bodies that construct a plan and execute it,
  plus the two replay environments' `resolve_plan` methods"*.

The consequence is the one the module names: one gate call site and one projecting body
can now disappear from the tree with nothing going red. Because
`FLOOR_REMOVAL_INSTRUCTION` says a legitimate removal and an accidental one need the
same edit, the *only* protection against a silent loss is the floor being tight, and it
is not.

**How I verified it.** Loaded the module and called its own helpers:

```
projecting bodies: 14 floor 13
gate sites: 12 floor 11
resolved binder sites: 12 floor 12
```

The 12th gate scope printed as `src/ccf/products/resolver.py __call__()`; the 14th
projecting body as `examples/hw1-companies-over-revenue/deployment/projection.py
build_projection() 118`. On `main` the same constants read 9 / 11 / 11, so they were
re-measured mid-phase and then went stale again as 17-03 and 17-09 landed.

**Fix.** Raise both to the observed counts and rewrite both enumerating comments to
name the two new sites (the comment is the audit trail, and both currently describe a
tree that no longer exists):

```python
MINIMUM_GATE_CALL_SITES = 12   # + src/ccf/products/resolver.py::GovernedResolver.__call__
MINIMUM_PROJECTING_BODIES = 14 # + examples/hw1-companies-over-revenue/deployment/projection.py::build_projection
```

Consider also adding a red-on-drift assertion for the *upward* direction, since the
whole class of defect here is a floor silently falling behind its subject.

---

### BL-02 — `as_of=None` does not mean what the client API and the README say it means (BLOCKING)

**File:** `src/ccf/client/adapters/inprocess.py::InProcessAdapter.ask`,
`src/ccf/client/client.py::ProductClient.ask`,
`examples/hw1-companies-over-revenue/README.md`

**What is wrong.** `ProductClient.ask`'s docstring states the contract as:

> **The** `as_of=None` **rule.** `None` means *use the server's decision instant* — the
> producing deployment answers against its own clock, and the instant it used comes
> back on the served vessel.

and the README states the consequence for a reader as:

> Drop the flag and you get today's answer, which is the right default for a caller

Neither is true of the only shipped transport. `InProcessAdapter.ask` computes

```python
asked_at=request.temporal_boundary or document.question.asked_at
```

and `document.question.asked_at` is a **literal from `binding.yaml`** —
`asked_at: "2026-03-02T12:00:00+00:00"` for HW-1. No clock is read anywhere on the
path. `QuestionDeclaration`'s own docstring is honest about this ("declared rather than
read from a clock so a deployment's answers reproduce"), so the tree contains both the
true statement and the false one, one module apart.

The observable consequence is not cosmetic. `GovernedResolver.__call__` sets
`expires_at = request.asked_at + timedelta(seconds=product_ttl_seconds)`, so a
default-path run today serves a product with `expires_at = 2026-03-02T12:10:00Z` —
five and a half months in the past — and `consume.py` prints it as
`answer expires 2026-03-02 12:10:00+00:00`. Gate 3 passes because `run_gates` is called
with `now=request.asked_at`, so nothing in the fabric objects; a consumer comparing
`expires_at` against wall clock sees every default answer as already dead.

`QuestionDeclaration.asked_at`'s remedy sentence is also incoherent as written: *"a
deployment wanting wall-clock behaviour states an instant here"* — stating a fixed
instant is precisely what forecloses wall-clock behaviour.

**How I verified it.** Read `inprocess.py::InProcessAdapter.ask`,
`binding_document.py::QuestionDeclaration`, `binding.yaml` (line `asked_at:
"2026-03-02T12:00:00+00:00"`), `resolver.py::GovernedResolver.__call__` (the
`expires_at` arithmetic and `run_gates(..., now=request.asked_at)`), and
`consume.py::main` (the `result.expires_at` print). `datetime` is always truthy, so the
`or` has no falsy-datetime escape.

**Fix.** Pick one and make the tree say it once:

1. **Honour the documented contract** — let the deployment declare *how* it answers a
   boundary-less question, with `now` as an admissible declaration, and default
   `asked_at` to the adapter's clock when the document does not pin one; or
2. **Correct the contract** — say `as_of=None` means *the instant the deployment
   declared for boundary-less questions*, drop "its own clock" from
   `ProductClient.ask`, and replace the README's "you get today's answer" with the
   truth. Then either raise `product_ttl_seconds` past the declared instant's age or
   state in the README that the default path deliberately serves an expired vessel.

Option 2 is the smaller change and is consistent with `D-32`'s reproducibility posture;
either way, `ProductClient.ask` is a public contract and cannot keep a false sentence.

---

### CR-01 — The premise route's condition 5 checks the constructor keyword, not the declared operator set (IMPORTANT)

**File:** `tests/products/test_gate_two_call_shape.py::_sdk_supplied_operator_set`

**What is wrong.** Condition 5's docstring says: *"Every plan it constructs is built
from that parameter … A factory that builds its plan from some other source has
authored a second operator set the Control Plane does not know about."* The
implementation reads `_constructed_plan_sources(scope, plan_classes)`, which resolves
the `required=` **keyword of the construction call**. But the operator set the
`ProjectionEngine` actually resolves against is the plan's `required_operators()`
return, which lives in a different lexical scope and is never read here.

So a factory can satisfy condition 5 with `return Plan(required=required, …)` while its
plan's `required_operators()` returns a locally-authored tuple, and the exemption is
granted. Today's shipped
`examples/hw1-companies-over-revenue/deployment/projection.py::_OverRevenueProjection.required_operators`
returns `self._required` verbatim, so nothing is wrong in the tree — but the gate is not
what is holding it that way.

**Mitigation that does exist, stated so this is not over-claimed.**
`GovernedResolver.__call__` builds `ProductLineage(operators_invoked=frozenset(required))`
from the declaration and hands `engine_resolved=execution.operators_invoked` to
`run_gates`, so a plan declaring a divergent set is refused at Gate 2 at runtime. The
AST gate is the weaker of the two guards, not the only one.

**How I verified it.** Read `_sdk_supplied_operator_set` and `_constructed_plan_sources`
against `_scope_nodes`/`_scopes` (which partition by lexical body, so
`_OverRevenueProjection.__init__` and `.required_operators` are outside the scanned
scope), then read `resolver.py::GovernedResolver.__call__` for the runtime backstop.

**Fix.** Either extend condition 5 to also require that the constructed class's
`required_operators` body returns the stored parameter, or narrow the docstring to say
what is actually checked ("every plan *construction* is handed that parameter") and
name Gate 2 as the guard for the declared set.

---

### CR-02 — The premise route's headline claim is contradicted by its own condition 2 (IMPORTANT)

**File:** `tests/products/test_gate_two_call_shape.py::_sdk_supplied_operator_set`,
`tests/products/test_gate_two_call_shape.py::_registers_requirements`

**What is wrong.** The docstring opens *"**Positively signalled, never inferred from
absence.** Five conditions, and each one is a fact readable from the tree rather than a
gap in it"* and then states condition 2 as *"That deployment registers **no**
`ccf.projection-requirements`."* That is an inference from absence, in the direction
that **grants** the exemption. `_registers_requirements` is fail-open in isolation:

```
_registers_requirements(Path("/nonexistent-root")) -> False
_registers_requirements(None)                      -> False
```

`(root / "artifacts").rglob("*.yaml")` on a missing directory yields nothing silently —
the exact `rglob` leniency this phase already identified as the root cause of its
dominant defect class.

**What saves it, stated precisely.** The composition is fail-closed because
`_deployment_root` runs first and returns `None` for anything outside `examples/` or
without a Control Plane authoring surface, so the "zero documents scanned" state is
unreachable through `_sdk_supplied_operator_set`. But the scan surface is still narrower
than the deployment: only `<root>/artifacts/**/*.yaml` and `<root>/ccf_config.yaml` are
read. HW-1's `scenario.yaml` sits in the same directory and is never scanned.

There is also an unstated sixth condition — `isinstance(scope, ast.FunctionDef |
ast.AsyncFunctionDef)` — not among the five the docstring enumerates.

**How I verified it.** Executed `_registers_requirements` against a nonexistent path and
against `None`; executed `_deployment_root` against `src/ccf/client/client.py` (returns
`None`); read both functions.

**Fix.** Restate the docstring honestly ("four positive conditions plus one negative
one, and here is why the negative one is safe: `_deployment_root` closes the vacuity
case"), and either widen `_registers_requirements` to every `*.yaml` in the root or say
in its docstring why the two locations are exhaustive.

---

### WR-01 — `encode_outcome` and `decode_outcome` are unreachable from every shipped code path (IMPORTANT)

**File:** `src/ccf/client/codec.py::encode_outcome`, `src/ccf/client/codec.py::decode_outcome`

**What is wrong.** `codec.py`'s module docstring claims *"`D-13` sends even the
in-process adapter through this codec rather than past it … a parity bug has exactly one
place to live"*. The only shipped adapter goes past it. `InProcessAdapter._encode`
constructs `WireOutcome` directly, computing the vessel with
`ccf.contracts.canonical.canonical_bytes` and the address with `hashlib.sha256`, and
`ProductClient._result_from` consumes the object with `check_outcome`. Neither
`encode_outcome` nor `decode_outcome` is called anywhere outside tests.

The consequence is narrower than "dead code": the `WireOutcome` **envelope's own**
serialization round trip — the part that carries `refusal`, `replay_ref` and the
`request` echo across canonical JSON — is exercised only by `tests/client/test_codec.py`.
The first real transport is the first thing that will exercise it under load, and the
"one place a parity bug lives" property does not currently hold for the encode half.

**How I verified it.**

```
$ command grep -rn "encode_outcome\|decode_outcome" --include=*.py src runtime examples tests tools
```

returns only `src/ccf/client/codec.py` (definitions), two prose mentions in
`client.py`/`wire.py` docstrings, and eleven lines in `tests/client/test_codec.py`.

**Fix.** Either route `InProcessAdapter._encode` through `encode_outcome` and its `ask`
return through `decode_outcome` (which is what `D-13`'s "true degenerate wire" claim
asserts and costs the microsecond the docstring already budgets), or amend the module
docstring to say that the shared path is `check_outcome` and that the envelope codec is
for wire transports only.

---

### WR-02 — The SDK's headline usage pattern does not pass `mypy --strict` (IMPORTANT)

**File:** `examples/hw1-companies-over-revenue/consume.py::main`,
`src/ccf/client/result.py::Result.refused`

**What is wrong.** The two-line example is reproduced verbatim in
`src/ccf/client/__init__.py`, `src/ccf/client/client.py`, `src/ccf/client/result.py` and
the example:

```python
if result.refused:
    log(result.refusal.reason, result.refusal.key)
```

`Result.refused` is a plain `bool` property, so it narrows nothing, and
`Result.refusal` is typed `Refusal | None`. Every adopter who runs `mypy --strict` — the
project's own standard, `[tool.mypy] strict = true` — gets two `union-attr` errors on the
first thing the README tells them to write. `[tool.mypy] files = ["src", "runtime"]`
excludes `examples/`, so nothing in CI catches it.

`result.py` records an accepted trade-off ("mypy cannot statically prove the caller
checked `refused`") but that trade-off is about the **guarded** post-assembly fields.
`refusal` is a pre-assembly field, is declared Optional, and is dereferenced by the
canonical snippet — a separate and avoidable problem.

**How I verified it.**

```
$ MYPYPATH=/home/parkave/ccf_code/src .venv/bin/python -m mypy --strict examples/hw1-companies-over-revenue/consume.py
examples/hw1-companies-over-revenue/consume.py:51: error: Item "None" of "RefusalEnvelope | None" has no attribute "reason"  [union-attr]
examples/hw1-companies-over-revenue/consume.py:51: error: Item "None" of "RefusalEnvelope | None" has no attribute "key"  [union-attr]
Found 2 errors in 1 file (checked 1 source file)
```

Those are the only two errors — `src/` itself is clean under the same invocation.

**Fix.** Add a narrowing accessor that costs no exported name, e.g.

```python
def is_refused(self) -> TypeIs[_RefusedResult]: ...
```

or, minimally and without a type-system change, rewrite the four copies of the snippet
to bind first (`refusal = result.refusal; if refusal is not None:`) and add `examples`
to `[tool.mypy] files` so the pattern the docs teach is the pattern CI checks.

---

### WR-03 — A non-finite declared debt factor raises `decimal.InvalidOperation`, not the documented `ValueError` (WARNING)

**File:** `src/ccf/client/adapters/binding_document.py::_decimal`,
`src/ccf/products/debt_scorer.py::DeclaredFactor`

**What is wrong.** `_decimal` guards only against `InvalidOperation` at construction, and
`Decimal("NaN")` constructs successfully. `DeclaredFactor.__post_init__` then evaluates
`not _ZERO <= self.value <= _UNIT`, and Python's `decimal` **signals** on an ordering
comparison with NaN rather than returning `False`. So a deployment writing
`debt: {completeness: "NaN"}` in `binding.yaml` gets a bare `decimal.InvalidOperation`
from inside a dataclass `__post_init__`, with no mention of the field, the file, or the
`[0, 1]` interval — losing every diagnostic `_decimal` and `DeclaredFactor` were written
to provide. `build_governed_resolver`'s `Raises:` block, which promises `ValueError: a
declared factor lies outside [0, 1]`, is wrong for this input.

**How I verified it.**

```
NaN      refused: InvalidOperation      <- wrong exception, no message
Infinity refused: ValueError            <- correct
-1       refused: ValueError            <- correct
2        refused: ValueError            <- correct
```

and `Decimal("NaN")` constructs without raising, so `_decimal` passes it through.

**Fix.** Refuse a non-finite decimal where it is authored:

```python
value = Decimal(raw)
if not value.is_finite():
    raise BindingError(f"`{key}.{field}: {raw}` in {document} is not a finite decimal")
```

`ccf.contracts.canonical::_normalize` already takes exactly this posture
(`"non-finite Decimal is not encodable"`), so this is copying a rule the tree already
holds rather than inventing one.

---

### WR-04 — `Result.content_address`'s docstring contradicts what `_result_from` stores (WARNING)

**File:** `src/ccf/client/result.py::Result.content_address`,
`src/ccf/client/client.py::ProductClient._result_from`

**What is wrong.** The property documents itself as *"Never the value the wire claimed:
the recomputation happens on the one decode path"*. In fact `check_outcome` calls
`verify_content_address` and **discards its return**, and `_result_from` then passes
`content_address=outcome.content_address` — the wire's own claim — into `Result`. The
values are equal because `verify_content_address` raises when they are not, so there is
no behavioural defect today; but the docstring asserts a property of the *stored value*
that the code does not have, and it is exactly the sentence a future reader would rely
on if the comparison were ever relaxed or reordered.

**How I verified it.** Read `codec.py::check_outcome` (return value of
`verify_content_address` unused at the call site), then `client.py::_result_from`.

**Fix.** Have `check_outcome` return the recomputed address alongside the vessel and
have `_result_from` store *that*, which makes the docstring true by construction and
gives the check a second load-bearing consumer. Or amend the docstring to "checked
against a recomputation on the one decode path".

---

### WR-05 — The client-example purity and budget gates cover a hand-maintained list of one (WARNING)

**File:** `tests/examples/test_client_example_purity.py::CLIENT_EXAMPLE_ROOTS`

**What is wrong.** `CLIENT_EXAMPLE_ROOTS` is a literal one-element tuple that both the
purity gate and the budget gate parametrize over. A second client example — the
explicitly anticipated next step, since the MCP adapter is the named `D-24` revisit
trigger — is silently ungated by both: no assertion goes red, no count is checked, and
the new example simply is not in the parametrization.

Both modules are otherwise exemplary about vacuity (`"Zero matches is a failure, not a
pass"`, `test_the_gated_client_examples_exist`), which makes the growth path the one
uncovered surface. The gates are immune to *shrinking* to nothing and blind to the tree
*growing* past them.

**How I verified it.** Read `CLIENT_EXAMPLE_ROOTS` and both gates' parametrize
decorators and precondition tests. No test compares the tuple against a discovered set.

**Fix.** Derive the roots (every `examples/*/` whose README declares a budget, or every
root whose top-level modules import `ccf.client`) and keep the literal tuple as a floor
assertion — the same instrument `MINIMUM_*` already uses elsewhere in this tree.

---

### WR-06 — `binding.yaml`'s `connection:` accepts credential material with nothing refusing it (WARNING)

**File:** `src/ccf/client/adapters/binding_document.py::_connection`

**What is wrong.** `_connection` accepts arbitrary scalar values under arbitrary
adapter-declared names and forwards them into `load_config_and_boot`. Its docstring says
*"A credential never belongs here"* — advice only. Meanwhile the credential path the SDK
does own (`DeploymentConfig.backend_secrets` → `SecretReference` → environment variable,
with `_preflight_adapter` refusing a `backend_secrets` entry that names a
non-credential field, and message hygiene explicitly forbidding value interpolation
because "one of those values is a credential", T-15.4-05) lives in `ccf_config.yaml` and
is **not reachable from `binding.yaml` at all**.

So the one document a client's binding address points at is the one document with no
secret indirection and no refusal, and a deployment whose backend needs a credential has
no in-document way to express it except inline. This module's own thesis is *"an
exception with no mechanism holding it narrow is not an exception; it is a precedent"* —
applied to `plan:` with two independent checks, and not applied here.

**How I verified it.** Read `_connection`; confirmed `backend_secrets` is a field of
`DeploymentConfig`/`DeploymentManifest` and is threaded from `config.backend_secrets` in
`src/ccf/deployment/config.py`, with no path from the binding document; read
`manifest.py::_preflight_adapter` and its secret-field refusal.

**Fix.** At minimum, refuse a `connection` setting whose name matches the declared
adapter's `secret_fields` and point the author at `backend_secrets` — the adapter
registration already publishes that set, so this is a lookup, not a new vocabulary.

---

### WR-07 — HTTP route handles moved from boot-time required to first-call 503 (WARNING)

**File:** `runtime/ccf_runtime/http_api/dependencies.py::ApiDependencies`

**What is wrong.** Five handles (`workflow_factory`, `workflow_engine`,
`hitl_transport`, `skill_catalog`, `grant_ledger`) changed from required to
`None`-defaulted. A deployment that forgets one now boots green and fails at first call
with `ERROR_ROUTE_HANDLE_ABSENT`. This is ruled (`D-IMPL-126` item (3)) and the module
discloses the tradeoff in its own words ("This change is not free and is not presented
as free"), which is why it is a WARNING and not a blocker — but it is structurally the
same shape as the rest of this review: a check that used to fire loudly and early now
fires quietly and late, in a phase whose defect class is exactly that.

**How I verified it.** Read the diff of `dependencies.py` and `errors.py` against `main`.

**Fix.** No code change requested. Ship an assertable helper the docstring already
recommends in prose ("a deployment that was relying on the boot `TypeError` … should
assert its bundle explicitly instead") — e.g. `ApiDependencies.require(*fields)` — so
the recommendation is mechanism rather than advice.

---

### IN-01 — `envelope_for` stringifies `key`/`reason`/`detail` unconditionally (ADVISORY)

**File:** `src/ccf/products/refusal.py::envelope_for`

`key = str(getattr(refusal, "key"))` produces the string `"None"` for any refusal type
that declares `key: str | None`. Verified that no shipped refusal type does — all
sixteen declare `key`, `reason` and `detail` as non-optional where they declare them at
all — so this is latent, not live. It is worth a guard because the module's whole
premise is that a field added next year appears without an edit here.

### IN-02 — `_unstable_parameter`'s refusal names the wrong thing on a non-string key (ADVISORY)

**File:** `src/ccf/client/wire.py::_unstable_parameter`

For a non-`str` mapping key the function returns `(path, key)`, and
`_parameters_survive_the_wire` renders it as `f"{path} is a {type(offending).__name__}"`
— reporting *the containing mapping's* path as being of the key's type. The check is
correct; the message misleads.

### IN-03 — `InProcessAdapter` re-parses `binding.yaml` on every `ask()` but honours the cached copy (ADVISORY)

**File:** `src/ccf/client/adapters/inprocess.py::InProcessAdapter._ensure_booted`

`load_binding_document(self._address)` runs per call (disk read + YAML parse + full
validation) purely to compute the cache key, and `ask` then reads `booted.document` for
the question, perspective and debt declarations. An edited `binding.yaml` is therefore
honoured for root resolution and silently ignored for everything else. Stating the
process-lifetime freeze in `_BootedDeployment`'s docstring would close it.

### IN-04 — The retirement sweep's dissolution claim now rests on the example this phase shipped (ADVISORY)

**File:** `tools/docs_tests/test_retirement_sweep.py::HEAD_ABSENT_SHAPES`

The `inline-tree-witness` row dissolved because
`examples/hw1-companies-over-revenue/consume.py` supplies a second `required=`-passing
non-plan call. Verified: exactly two witnesses at HEAD —
`examples/03-harness-portability/run.py:693` and
`examples/hw1-companies-over-revenue/consume.py:30`. Making `--min-revenue` optional
(an entirely plausible ergonomic edit) restores the row and turns
`test_every_no_path_token_shape_is_accounted_for_at_head` red. The design accounts for
this and the failure message says what to do, so this is disclosure rather than a
defect — but the phase's own example is now load-bearing for a docs-tooling assertion
and nothing at `consume.py` says so.

### IN-05 — Unnecessary `# noqa: E402` (ADVISORY)

**File:** `examples/hw1-companies-over-revenue/consume.py`

The `import ccf.client.adapters.inprocess  # noqa: E402,F401` sits after a comment
block, not after code, so E402 cannot fire. In an 80-line budgeted file whose whole
point is that a reader can hold it entirely, a suppression for a rule that is not
triggered is a line the reader has to reason about for nothing. `F401` is genuinely
needed.

### IN-06 — `_integer` admits zero and negative TTLs (ADVISORY)

**File:** `src/ccf/client/adapters/binding_document.py::_integer`

`max_ttl_seconds: 0` and `product_ttl_seconds: -1` are accepted as "whole number of
seconds". A negative product TTL produces `expires_at < temporal_boundary`, which Gate 3
will report as a governed TTL refusal — i.e. a wiring error surfaces to the caller as a
refusal the fabric never meant to make. The same posture `_decimal` takes for `[0, 1]`
should apply here: refuse at authoring time.

### IN-07 — `InProcessAdapter._encode` reports a mistyped resolver return as a wire failure (ADVISORY)

**File:** `src/ccf/client/adapters/inprocess.py::InProcessAdapter._encode`

A resolver returning something that is neither `ServedProduct` nor `RefusalEnvelope`
raises `TransportError`, whose whole contract is *"the wire never spoke"*. That is a
deployment defect, not a wire defect, and the module elsewhere is scrupulous about this
distinction (`ProductNotResolvable` is deliberately *not* converted into a refusal for
exactly this reason). The branch is `# pragma: no cover`, so this is a taxonomy nit, not
a live path.

### IN-08 — `RULED_OUT_KEYS`' shape check cannot see a reference without a `.py` suffix (ADVISORY)

**File:** `src/ccf/client/adapters/binding_document.py::looks_like_a_reference`

`looks_like_a_reference` requires the module path to end in `.py`, so
`some_module:attr` in a data position passes the sweep. Not exploitable —
`load_reference` is called only for `REFERENCE_KEYS`, so nothing in a data position is
ever imported — but the docstring frames the sweep as closing "a second reference
through a key the schema *does* permit", and a spelling that omits `.py` is precisely
how a future adopter would smuggle one in prose before somebody wired it up.

---

## 3. The self-judged-example verdict

**Question:** do `tests/products/test_gate_two_call_shape.py` and
`tools/docs_tests/test_retirement_sweep.py` genuinely constrain
`examples/hw1-companies-over-revenue`, or were they shaped to admit it? And is
`_sdk_supplied_operator_set` really five positive conditions with two disjoint ceilings
of one?

**Verdict: genuinely constraining, with two soft spots and one stale floor. Not shaped
to admit — but shaped *around* the example closely enough that a reviewer should say
where.**

**What the claim gets right, verified by execution rather than reading.**

- The two ceilings are real and are exactly one each, with no headroom:
  `MAXIMUM_ONE_DOCUMENT_DEPLOYMENTS = 1`, `MAXIMUM_SDK_SUPPLIED_DEPLOYMENTS = 1`.
- The populations they bound are genuinely disjoint at HEAD, and I measured them
  rather than trusting `test_the_two_exemptions_are_disjoint`:
  `_one_document_deployments() == ['examples/s1-00-companies-over-revenue']`,
  `_sdk_supplied_deployments() == ['examples/hw1-companies-over-revenue/deployment']`.
  One claimant each; intersection empty. A second claimant of either is red.
- The exemption is not a licence. `_binder_collapses` property (1) — the tautology
  refusal — sits **outside** the `if demanded:` guards, so a body that claims the
  exemption and calls the binder anyway is still refused. I checked this in the source,
  not in the docstring that asserts it.
- The comparison the exemption removes really did move rather than vanish.
  `src/ccf/deployment/config.py::_refuse_operator_set_divergence` exists, is called
  unconditionally from `derive_deployment` before any operator entry is materialised, and
  compares `product_class.required_operator_keys` against the `operators:` section's own
  keys. HW-1 is a single-file `D-IMPL-136` deployment, so it runs at every boot.
- Conditions 1, 3 and 4 are genuinely positive and genuinely readable from disk.
  Condition 3 in particular — `binding.yaml`'s `plan:` must name *this module and this
  function*, resolved and compared against the scanned path — is the strongest of the
  five, and it is a claim the Control Plane makes on disk rather than an inference.
- The vacuity cases are closed at the composition level: `_deployment_root` returns
  `None` for anything outside `examples/` or without an authoring surface, so the
  fail-open `_registers_requirements` is unreachable through this route.
- `_binding_plan_reference` deliberately does **not** call
  `load_binding_document`, so an unrelated authoring mistake elsewhere in the document
  cannot take this gate down with it. That is the right call and is argued for in the
  docstring.

**Where the claim overstates itself.**

1. **It is four positive conditions and one negative one, not five.** Condition 2 —
   "registers **no** `ccf.projection-requirements`" — is an inference from absence, in
   the direction that grants the exemption, and it is stated as such three lines under
   a heading that says "never inferred from absence". See CR-02.
2. **Condition 5 checks the wrong artifact.** It reads the plan constructor's
   `required=` keyword, not the plan's `required_operators()` return, which is what the
   engine resolves against. A conforming-looking factory can earn the exemption while
   its plan declares a self-authored set; only Gate 2 at runtime catches that. See
   CR-01.
3. **There is an unstated sixth condition** (`isinstance(scope, FunctionDef |
   AsyncFunctionDef)`).

**The thing that actually looks like shaping, and it is not in the premise route.**
It is in the floors. The same phase, the same agent, added a projecting body and a
`run_gates` call site to the trees this module scans and left `MINIMUM_PROJECTING_BODIES`
and `MINIMUM_GATE_CALL_SITES` where they were. The result is a module whose docstrings
argue at length that headroom is a licence, carrying one unit of headroom on each of two
floors, both created by the artifact the module is judging. I do not read this as
deliberate — `MINIMUM_RESOLVED_BINDER_SITES` *was* re-measured correctly to 12, which is
what an agent gaming the gate would not have bothered with — but it is the single change
that most weakens this module, and it arrived in the same commit range as the example.
See BL-01.

**On the retirement sweep, briefly.** It was not shaped to pass. The replaced
assertions are genuinely stronger than what they replaced: `shape_accounting_problems`
and `dissolution_problems` are both functions of their inputs with parametrized controls
including an explicit empty-census / empty-source vacuity case, and
`per_row_ownership_problems` treats an empty row set as a failure rather than a pass.
The one softness is that `test_the_dissolution_check_refuses_a_returning_coupling`
builds its control from `head().rows` filtered by *file* rather than by *shape*, so it
would pass on a row of any shape — a weaker control than the docstring implies, but it
is testing the predicate, and the predicate is shape-agnostic by design.

## 4. What I verified and found sound

Recorded so coverage is legible, and so a later reader knows what was actually looked
at rather than glanced past.

- **The four-name surface.** `ccf/client/__init__.py::__all__` is exactly
  `BindingError, ProductClient, Result, TransportError`. `Refusal` is an alias of
  `RefusalEnvelope` (the same type, not a parallel copy — the right call, and argued
  for), and `RefusedResultError` is deliberately importable but unexported.
- **The `Result` guard.** `GUARDED_FIELDS` and `PRE_ASSEMBLY_FIELDS` partition the
  public properties; `_served_or_raise` reads `GUARDED_FIELDS` for its message so the
  enumeration cannot drift from the tests; `RefusedResultError` derives from
  `RuntimeError` and not `AttributeError`, which correctly defeats
  `getattr(result, "payload", None)` and `hasattr`; `__repr__` touches no guarded field.
  The three-way construction guard (both halves / neither / address-on-refusal) is
  enforced in `__init__`, not documented.
- **`WireOutcome._exactly_one_half`.** All four states are enforced at construction
  (both, neither, served-without-address, refused-with-address). A caller cannot
  construct their way around it.
- **`_parameters_survive_the_wire`.** The admissible set is genuinely narrower than the
  canonical serializer's, and for the right reason (a `Decimal` renders as text and the
  echo cross-check would then report a healthy wire as failed). Tuples excluded
  deliberately; recursion covers nested mappings and lists; non-`str` keys refused.
- **`verify_content_address`.** `sha256(product_json.encode("utf-8"))` is by
  construction the same digest as `content_hash` of the product, because
  `InProcessAdapter._encode` sets `product_json = canonical_bytes(product).decode("utf-8")`
  and the round trip is the identity. Recomputation is authoritative; the claim is never
  trusted.
- **The refusal taxonomy.** `envelope_for` dispatches on exact type, never `isinstance`
  — correct, and the docstring's reason (an unknown subclass would be flattened to its
  nearest known ancestor and produce a well-formed envelope carrying the wrong kind) is
  the right reason. `REFUSAL_KINDS` covers sixteen types; the two allowlists close the
  `…Refusal` and `…Violation` name halves by set equality against a structural walk. I
  reflected over every type in `REFUSAL_KINDS` and confirmed no `key`, `reason` or
  `detail` field is Optional today, so the `str()` coercions are safe (see IN-01 for the
  latent case).
- **`_PRE_ASSEMBLY_REFUSALS`.** `envelope_for` refuses a lineage alongside a
  `ProductRequestViolation`, and `GovernedResolver.__call__` correctly passes no lineage
  on the request-conformity branch and `candidate.lineage` on the gate branch. `D-09`'s
  assembly boundary is structural on both sides.
- **`GovernedResolver` ordering.** Address check → request check → graph read at the
  question's boundary → operators → Π → register → gates → record → serve. Nothing
  reaches `fabric.handle.worker`; the composition has a reader and no writer, so
  single-writer holds by construction. Gate 2's two sides come from the declaration and
  from the engine respectively, which is two sources and not one.
- **`build_governed_resolver`'s two-shape refusal.** Both "neither" and "both" are
  `TypeError`s, `is not None` is used throughout so `Decimal(0)` is not mistaken for
  absence, and `missing` is computed by name rather than by position against
  `DEBT_SCORER_INPUTS` (the docstring's stated reason is correct — a positional zip would
  misreport after a reorder).
- **`AssemblyDebtScorer`.** The empty-assembly branch fails closed with `D_c = 1` and
  `NO_SCORER_PINS` — correctly refusing to name a scorer as the producer of zeroes it
  did not measure. Observations are typed by `entity_class` and dated by `observed_at`,
  and `now` comes off `view.as_of`, never a clock, so the figure re-computes at replay.
- **Path containment in `binding_document.py`.** `_contained` applies both checks and
  neither subsumes the other: the written-form check refuses an absolute path or a `..`
  segment, and the resolved-form check closes a plain name that is a symlink out of the
  root. `load_reference` names the module after a digest of the resolved root, so two
  deployments carrying `projection.py` do not shadow each other in `sys.modules`; the
  residual (same-named siblings) is stated rather than hidden.
- **`_preflight_adapter` message hygiene.** Refusals are built from names only and the
  supplied value is never interpolated, because one of those values may be a credential
  (T-15.4-05). Confirmed still true after this phase's edits.
- **`ServableProduct`'s pydantic refusal.** Both channels are covered (metaclass for
  class lookups, `__getattr__` for instance lookups) reading one frozenset, and
  `ServableProductNotAModel` derives from `AttributeError` as well as `GateBypassError`
  so `hasattr` degrades instead of exploding. `__call__` is not overridden and the gate
  token check is untouched — no construction path is added.
- **The conformance suite.** `result_fields` derives the compared field set from
  `Result`'s own properties cross-checked against the two published tuples, so a field
  added next year joins without an edit. `assert_decision_instant_is_auditable` does not
  merely recover an instant — it re-asks pinned to it and requires an identical content
  address, which is what makes the recovery a measurement. Every leg does per-subject
  work that is non-vacuous with one subject, and `test_the_suite_fires.py` runs the same
  functions over a divergent subject and requires each to fail.
- **The budget gate.** `declared budget: 80 lines` parses out of the README;
  `consume.py` is 78 physical lines; `check_example_budget` returns a violation for a
  missing root, a missing README, zero or two budget declarations, and a root with no
  top-level module — every vacuity case is a failure, not a pass.
- **Green at HEAD.** `pytest tests/client tests/products/test_gate_two_call_shape.py
  tests/examples -q` → 770 passed, 37 skipped. `python -m tools.lints --all` → silent.
  `mypy --strict` over `src` + `runtime` → clean (the only errors I could produce were in
  `examples/`, which is outside `[tool.mypy] files`; see WR-02).

## 5. Risk assessment

**Highest residual risk: the floors.** BL-01 is one line each to fix, but it is the
class of defect this phase exists to have eliminated, and it landed *inside the module
that judges the example*. Until it is fixed, one gate call site and one projecting body
can leave the tree with nothing going red — and because `FLOOR_REMOVAL_INSTRUCTION`
concedes that a legitimate and an accidental removal need the same edit, the floor being
tight is the only distinguishing signal there is.

**Second: the `as_of=None` contract.** BL-02 is a false statement in a public API
docstring and in the adoption README, with an observable wrong-looking output (an
expired product) on the default path. An adopter's first reaction will be that the SDK
is broken; it is not, but nothing in the tree will tell them that. This is the finding
most likely to cost adoption credibility.

**Concentration risk in the gate module.** `tests/products/test_gate_two_call_shape.py`
is 4,522 lines carrying three tripwires, three floors, two ceilings, a disjointness
proof and roughly forty controls. It is genuinely well-built, and it is a single point
of comprehension: CR-01 and CR-02 are both cases where a claim in a docstring is a little
stronger than the code beneath it, and at this size that gap is very hard for the next
reader to spot. If the module grows again, splitting the premise routes into their own
module with their own controls would buy more than another control will.

**Low residual risk elsewhere.** WR-01 is a claim/implementation gap with no live
consequence until a second transport ships — but it will bite exactly then, which is the
MCP adapter, which is next. WR-06 is a posture gap rather than a live vulnerability;
nothing in the tree puts a credential in `binding.yaml`, and `_preflight_adapter`'s
`extra=forbid` still refuses settings the adapter does not declare. WR-03, IN-06 and
IN-02 are all "the refusal fires but says the wrong thing" — small, cheap, and worth
fixing together in one pass over `binding_document.py`'s validators.

**What I could not assess.** The example cannot run from a clean checkout (deliberate,
recorded), so I judged the `expires_at` consequence in BL-02 by reading the arithmetic
rather than by observing output. If that reading is wrong, BL-02 collapses to a
documentation-only finding — but the arithmetic is three lines and unambiguous.

---

_Reviewed: 2026-08-16_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
</content>
</invoke>
