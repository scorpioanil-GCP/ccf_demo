---
phase: 18-mcp-transport-the-second-door-and-the-portability-proof
kind: close-time-review
reviewers: [codex/gpt-5.5, cursor, gemini, gsd-code-reviewer]
subject: shipped code at `phase-18` @ e3fb143
status: triaged-pending-ruling
date: 2026-08-17
---

# Phase 18 — Close-Time Review Panel

Per `CLAUDE.md` §3.1. This panel reviewed the **shipped code**, not the plans; the
plans were reviewed before execution and those decisions are already executed. This
file is deliberately distinct from any pre-execution plan review so that review
survives.

Every panelist was given the five known findings (KF1–KF5) and told **not to
re-derive them** — the budget was pointed at what is *adjacent* to each. Every
panelist was also told the project's recurring defect class (an assertion that
passes because it compares nothing) and asked to find the next instance.

**Every finding below was verified against the tree before being recorded.**
Rejected findings are recorded as rejected, per §3.1.

## Panel composition and what each contributed

| Reviewer | Grounded? | Findings | Confirmed | Rejected |
| --- | --- | --- | --- | --- |
| **Cursor** | yes | 10 + a "checked, not defects" section | high | — |
| **Codex** (gpt-5.5) | yes, after remediation | 4 + a security note | 4 | 0 |
| **Gemini** | **no** | 5 | 0 | 4 (+1 partial) |
| `gsd-code-reviewer` | yes | pending at time of writing | — | — |

### Codex ran twice, and the first run is worth recording

Codex's first invocation returned **exit 0 with no findings**: its bubblewrap sandbox
could not create user namespaces (`bwrap: loopback: Failed RTM_NEWADDR: Operation not
permitted`), so every filesystem command failed before running. **It refused to
fabricate a review rather than producing plausible findings from the brief alone**,
which is the correct behaviour and is recorded here as such.

The operational lesson is the phase's own defect class appearing in the *review
tooling*: **exit code 0, well-formed output, zero actual verification.** A panel
scored by exit status would have counted this as a clean pass from a reviewer that
never opened a file. It was re-run with the two primary source files inlined and
line-numbered, and produced four confirmed findings.

### Gemini was ungrounded and its findings were mostly fabricated

Four of five Gemini findings cite **symbols that do not exist anywhere in the tree**.
This is the project's fourth through seventh confident, well-formatted, false finding
from a reviewer. See "Rejected findings" below.

## CONFIRMED — BLOCKING

### B0. Both client-seam integrity checks are inert on the shipped adapters
*`gsd-code-reviewer` CR-02. The depth pass found this; no panelist did.*
**This is the defect class in `src/` — mechanism, not verification code.**

`src/ccf/client/codec.py:30-42` states the design principle in its own words: the
echo is **cross-checked, not reconstructed**, because reconstruction *"cannot detect a
transport that answered a different question … a proxying or multiplexing transport
that crosses two in-flight questions produces a perfectly well-formed outcome for the
wrong request, and a client that reconstructs the identity from its own state would
label that answer with the question it meant to ask."*

The shipped adapter reconstructs. Verified:

1. `DoorOutcome` carries **no request identity** — its members are `product_json`,
   `replay_ref`, `refusal` (`door.py:139-141`).
2. `mcp_stdio._decode` therefore sets `request=request` from its own argument
   (`mcp_stdio.py:398,406`) — client state, not the wire.
3. `client.py:172` passes that **same object** as `sent`:
   `self._result_from(self._adapter.ask(request), sent=request)`.
4. So `check_outcome`'s `if outcome.request != sent` (`codec.py:166`) compares an
   object with itself. **It cannot fail.**

The same holds for `verify_content_address` (`codec.py:116`): the "claimed" address is
computed by the adapter from the identical `product_json` it emits
(`mcp_stdio.py:407-409`, `inprocess.py:439`), so the check is
`sha256(x) != sha256(x)`. Its docstring says *"the claimed one is never trusted … the
whole value of a content address is that the claim is checkable."*

Both checks are inert **on the one transport where a crossed-question wire is
physically possible**. The phase's own `_AnswersAnotherQuestion` control is exactly
that failure, and it is caught only by the *cross-adapter parity diff* — protection no
adopter running a single transport has.

### B0b. A naive `as_of` breaks the portability claim, reproduced
*`gsd-code-reviewer` CR-01, reproduced by running both README commands.*

With `--as-of 2026-08-01T00:00:00` (naive):
- `inprocess:` → `ccf.contracts.canonical.CanonicalizationError` escaping
  `ProductClient.ask` (from `graph/backends/sqlite.py:343`)
- `mcp+stdio:` → `ccf.client.errors.TransportError`

Same question, two exception classes — and `ProductClient.ask`'s `Raises:` block
(`client.py:161-165`) names only `TransportError`. The `mcp+stdio` path reports a
**transport failure for a caller's malformed argument**, the `D-10` inversion. The
guard for this hazard exists one field away: `WireRequest._parameters_survive_the_wire`
(`wire.py:140-175`) refuses `parameters` values that cannot survive the wire and argues
the general principle in its docstring; `temporal_boundary` (`wire.py:138`) got no
equivalent. No conformance `Question` uses a naive instant, so nothing catches it.

### B1. A served answer can carry `replay_ref=None`, and parity is satisfied by mutual absence
*Found independently by Codex (#1) and Cursor (#4) — two reviewers converging.*

`src/ccf/products/door.py:228` — `served_answer()` returns
`ServedAnswer(product=..., replay_ref=None)` when the resolver answers with the
narrower `ServableProduct` rather than `ServedProduct`. The MCP adapter propagates
that `None` unchanged (`src/ccf/client/adapters/mcp_stdio.py:404`).

**Why this is the vacuity class surviving inside KF1's own fix:**
`assert_served_parity` compares `replay_ref` across subjects. If *both* subjects
emit `None`, they agree perfectly while carrying nothing — exactly the shape
`D-IMPL-148` was ruled to prevent. Verified: **no conformance leg asserts that a
served delivery carries a replay reference.** The only such assertion in the tree is
`tests/client/test_data_only_deployment.py:232`, a single test of one deployment
shape, not a parity leg.

Plan `17-10` Task 2 *recorded* this precondition in prose ("the conformance fixture's
resolver must be a `GovernedResolver`") but nothing enforces it. The parameter table
got a non-vacuity guard for precisely this reason ("refuses a table in which no case
is served"); the replay-ref parity has no equivalent.

### B2. The MCP door defaults `parameters` while its own docstring says it does not
*Cursor #3.*

`runtime/ccf_runtime/mcp/egress.py:732` — `parameters=dict(parameters or {})`.
The handler docstring at `egress.py:604-611` states the handler *"forwards the mapping
**verbatim**. It coerces nothing, defaults nothing and inspects nothing."*
`or {}` is a default, and `dict()` over a sequence of pairs is a coercion.

Consequence, and it is a door disagreement of the exact kind Task 1 shipped a table to
prevent: JSON-RPC `"parameters": null` arrives as `None` and becomes `{}` on MCP —
served. The same payload on HTTP is `400 ERROR_PRODUCT_PARAMETERS_MALFORMED`
(`routes/product.py:453-468`). The width table cannot see it: its five cases are all
well-formed JSON objects (`tests/mcp/test_egress_parameters.py:594-600`).

### B3. The KF3 fix's own test cannot fail on omission
*Cursor #10c.*

`tests/contracts/test_canonical.py:277,282` — `set(carried) <= PERMITTED_CHILD_VARIABLES`
is one-sided. It fails on an *extra* variable and cannot fail on a *missing* one. The
`PYTHONPATH` repair itself is checked by name, but the "the set stays closed" claim is
half a claim. Same class as the leg `D-IMPL-149` just split.

## CONFIRMED — ADVISORY

- **A1 (Codex #3).** The refusal half of `assert_decision_instant_is_auditable`
  (`suite.py:755-767`) checks only that `temporal_boundary is not None`. It has no
  timezone-awareness check (the served half has one at `suite.py:710`) and never
  verifies the instant was resolved by re-asking. A transport stamping any datetime
  passes.
- **A2 (Codex #4).** `door_refusal()` returns a pre-existing `RefusalEnvelope`
  untouched (`door.py:299`) while the constructed path builds `RequestIdentity` from
  the current request (`door.py:311`). A resolver returning a stale envelope for a
  different question would have it published as this question's governed answer.
- **A3 (Codex #2).** `assert_one_instant_is_one_decision`'s *cross-subject* half is
  vacuous with one subject — `_require_subjects` (`suite.py:202`) refuses only an
  empty collection. The in-process binding calls it with one subject. The leg's
  per-subject half is genuinely non-vacuous, and the MCP binding supplies two, so the
  agreement claim *is* exercised — but it would silently stop being exercised if the
  MCP binding were removed. Consistent with `assert_served_parity`'s documented
  precedent.
- **A4 (Cursor #1, #2).** Two further door asymmetries, both pre-existing and one
  already recorded as `DIV-4`: a fabric refusal is recoverable on MCP but produces an
  unshaped 500 on HTTP (`served_answer` raises `TypeError` for a `RefusalEnvelope`;
  `routes/product.py:191` always calls it); and a naive `asked_at` is a named door
  refusal on MCP (`egress.py:703-712`) but passes through on HTTP
  (`routes/product.py:410-423`, zero `tzinfo` checks in the HTTP package).
- **A5 (Cursor #5, security).** Stdio auth is impersonation rather than verification:
  `serve.py:276-284` and `tests/client/fixtures/stdio_server.py:173-181` plant an
  `AuthenticatedUser` on a ContextVar because FastMCP's bearer middleware is HTTP-only,
  and the adapter never sends a token. `token_verifier` / `AuthSettings` on a stdio
  server do nothing. Separately the child inherits the full parent environment
  (`mcp_stdio.py:322`, deliberate and documented per KF3) with no cwd jail and no
  program allowlist. **Codex's independent judgement:** the spawn itself is not a bug
  because `mcp+stdio` must launch a program; the issue is that the threat model
  ("the binding program is fully trusted deployment code") is not stated in
  user-facing docs. Note `CCF_BINDING` is an environment variable, so anyone who can
  set it already controls the process environment.
- **A6 (Cursor #6).** The MCP *resource* surface (`egress.py:456-508`) still returns
  bare `canonical_bytes` with `request=None` — no `replay_ref`, no refusal envelope.
  Same defect class as KF1, on the Pattern 3 surface the client adapter does not use,
  so conformance structurally cannot see it. Documented as deliberately unchanged.
- **A7 (Cursor #7).** `DoorOutcome` forbids a refusal carrying `replay_ref`
  (`door.py:166-172`), but `WireOutcome._exactly_one_half` (`wire.py:227-256`) and
  `Result.__init__` (`result.py:219-244`) do not enforce the same exclusivity. The
  producing-side invariant is not a property of the consuming seam.
- **A8 (Cursor #8).** Content-address recoverability is not analogous across doors:
  HTTP publishes `X-CCF-Content-Address` over the body bytes, so a zero-CCF client
  hashes `response.content` correctly; a raw MCP client hashing the tool return hashes
  the **envelope**, not the vessel. Works for a CCF client, which unwraps
  `product_json` first.
- **A9 (Cursor #9).** No timeout on the child; one spawn and boot per `ask`; the test
  fixture never `close()`s its fabric handle where the example does
  (`serve.py:287-288`).
- **A10 (Cursor #10b).** `test_the_tool_carries_the_resources_bytes` uses a constant
  resolver, so it proves serialization identity but not that tool and resource answer
  the same *question* — the resource is called with `request=None`, the tool with
  `{minimum_score: 11}`.

## REJECTED — recorded per §3.1

### Gemini, 4 of 5

| # | Claim | Why rejected |
| --- | --- | --- |
| G1 | `execute_mcp_call` returns `CallResponse(…, meta={})`, dropping `replay_ref` | **Neither symbol exists anywhere in the tree.** `grep -rn "execute_mcp_call\|CallResponse" src/ runtime/ tests/` returns nothing |
| G2 | `suite.py:43,51,…,115` use `assert result` in `test_property_read_*`; always truthy | **Fabricated.** Those lines are docstring prose; no `assert result` and no such test names exist in the file |
| G3 | Adapter leaks children — manual `start()`/`stop()`, no `__aenter__` | **False.** No such API exists. Session lifetime is a scoped `async with stdio_client(...)` / `async with ClientSession(...)` inside `_call` (`mcp_stdio.py:328-329`); cleanup is guaranteed on exception |
| G5 | A broad `except Exception` may swallow `ProductEntitlementRefused` | **False.** `egress.py` contains **zero** `except Exception` clauses |
| G4 | "Unvalidated command execution — arbitrary binaries" | **Partial; mechanism wrong, severity overstated.** No `_parse_binding`, no `create_subprocess_exec`. Actual path: `shlex.split`, exactly-two-token check, `is_file()` check, then `command=sys.executable, args=[program, root]` — arbitrary *Python under the current interpreter*. Retained in weakened form as **A5** |

Gemini had no filesystem grounding in this run and reviewed the *description* of the
code in the brief rather than the code. The pattern to note: each fabricated finding
names a plausible-sounding symbol that fits the architecture's shape but is not in it.

### Earlier in this phase — the verifier

A prior finding that *"the only server program in the tree reaches the private
`_boot` — no public composition path for an adopter"* was rejected in `D-IMPL-150`.
`ccf.deployment.load_and_boot` and `load_config_and_boot` are public and in `__all__`;
`examples/04-cross-process/producer_child.py` uses them. The claim came from a `grep`
for `_boot` matching the substring inside `load_and_boot`.

## Panel dissent worth recording

Cursor and Codex disagree on the spawn's severity. Cursor rates it **High (security)**;
Codex explicitly declines to report the spawn as a bug, reasoning that `mcp+stdio` must
launch a program by definition, and locates the real issue in the undocumented threat
model. Recorded rather than resolved — it is a scope question for Dave.

## What the panel did NOT overturn

`git diff tests/client/conformance/suite.py` for plan `17-10`'s own work remains **0
lines** with a real second adapter bound and passing. No reviewer challenged the
portability claim, the adapter's `D-12`/`D-24` conformance, or the `D-IMPL-149` split —
Cursor explicitly checked the split and recorded it as structurally non-vacuous, noting
that `test_the_mcp_binding_fires.py:111-140` puts a genuinely divergent MCP subject
into the leg.
