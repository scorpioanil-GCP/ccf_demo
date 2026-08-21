---
phase: 20-client-access-from-three-harnesses-adk-anthropic-agent-sdk-a
reviewed: 2026-08-21T00:00:00Z
depth: standard
reviewer: claude (gsd-code-reviewer, single-agent pass)
scope_note: >-
  Additive to the cross-AI close panel in `20-CLOSE-REVIEWS.md`. B-1, B-2, B-3,
  A-1..A-4 are NOT re-derived here; R-1..R-4 are not resurrected. Every finding
  below was verified against the tree, and the two BLOCKERs were reproduced by
  running the shipped functions.
files_reviewed: 30
files_reviewed_list:
  - docs/DECISIONS.md
  - docs/retired/16-external-consumers/client_claude_agent.py
  - docs/retired/16-external-consumers/client_langgraph.py
  - docs/retired/16-external-consumers/README.md
  - docs/surface/examples/RETIREMENT-COUPLINGS.md
  - docs/surface/examples/SECTION-2-TRANSPORT.md
  - examples/external/00-hello-context/artifacts/experience.yaml
  - examples/external/00-hello-context/client_adk.py
  - examples/external/00-hello-context/client_anthropic.py
  - examples/external/00-hello-context/README.md
  - examples/external/00-hello-context/run.py
  - examples/hw1-harness-clients/client_adk.py
  - examples/hw1-harness-clients/client_anthropic.py
  - examples/hw1-harness-clients/client_langgraph.py
  - examples/hw1-harness-clients/README.md
  - examples/hw1-harness-clients/runner/drive.py
  - examples/hw1-harness-clients/runner/model-conversation.yaml
  - examples/hw1-harness-clients/runner/model_stub.py
  - examples/hw1-harness-clients/runner/question.yaml
  - examples/hw1-harness-clients/runner/scenario-rows.yaml
  - public/how-to/run-agents-cross-process.md
  - tests/examples/test_artifact_schema_headers.py
  - tests/examples/test_client_example_budget.py
  - tests/examples/test_client_example_purity.py
  - tests/examples/test_hw1_harness_clients_no_model.py
  - tests/examples/test_hw1_harness_clients_readme.py
  - tests/examples/test_hw1_harness_clients_retirement.py
  - tests/examples/test_hw1_harness_clients_wiring.py
  - tools/lints/no_hardcoding.py
  - tools/lints/tests/test_no_hardcoding.py
findings:
  critical: 2
  warning: 8
  total: 10
status: issues_found
---

# Phase 20: Code Review Report (single-agent pass)

**Reviewed:** 2026-08-21
**Depth:** standard
**Files Reviewed:** 30
**Status:** issues_found

## Summary

This pass was briefed with the close panel's verified findings and told to spend
its budget on what is *adjacent* to them: asymmetric matching elsewhere, AST
escape hatches in the other arms of `no_hardcoding.py`, guards that cannot fail,
No-Hardcoding / harness-neutrality across the shipped clients, and doc/code
drift. Nothing from `20-CLOSE-REVIEWS.md` is restated.

Two blocking findings came out of it, and both are the same defect *classes* the
panel already named, one level further out:

- **CR-01** is the `--live` half of criterion 6. The payload gate the phase
  added is unconditional, and its markers come from the seed document — so
  `--live`, which by ruling points at a deployment seeded with somebody else's
  data, fails by construction on every leg, with a message that misdiagnoses the
  cause. The three `--live` `make` targets that `test_hw1_harness_clients_readme.py`
  asserts exist are targets that cannot pass. This is `B-1`'s neighbourhood —
  the marker/payload surface — from the direction the panel did not look.
- **CR-02** is `B-2` generalized and measured. The destination arm's stated
  contract ("the value is FOLLOWED to the sink") holds for four spellings and
  fails for at least eleven, including `os.environ.get(NAME) or "<prompt>"` —
  the same env-var-worn-as-a-hat shape the arm was minted for. Fixing `B-2` as
  written (accept a keyword `default=`) does **not** close it.

The genuinely strong surfaces the panel identified stand up to a second read:
the AST purity gate and its `C-20-*` controls, the socket guard with its in-situ
arming probe, the criterion-7 diff assertion with its vacuity controls, and the
README element gate (whose marker matching, notably, normalizes *both* sides —
the symmetry `B-1` is missing).

Eight warnings follow. Two are guards that assert less than the prose beside
them claims; three are duplicated or divergent notions of one fact; three are
doc/code drift introduced or left by this phase.

## Critical Issues

### CR-01: `--live` fails by construction on every leg, and blames the client for it

**Files:**
`examples/hw1-harness-clients/runner/drive.py:1060-1061` (markers read),
`:1098` (payload gate, unconditional),
`:1126-1129` (`--live` subject selection),
`examples/hw1-harness-clients/runner/scenario-rows.yaml:116-141` (the markers),
`Makefile:470-477` (the three targets),
`examples/hw1-harness-clients/README.md:232-236, 248-252`.

**Issue.**

`_subject_factory` makes `--live` mean exactly one thing:

```python
def subject(name: str) -> pathlib.Path:
    if live:
        return SOURCE_DEPLOYMENT
    return stack.enter_context(seeded_subject(scratch / name))
```

`SOURCE_DEPLOYMENT` is the **tracked** `examples/hw1-companies-over-revenue/deployment`,
which ships unpopulated by ruling (`D-32`) and which the operator populates with
their own data — the sibling README's own sample output names
`Contoso Manufacturing`, not the six fictional companies this runner declares.

But `main()` reads the payload markers unconditionally, from the seed document,
with no `live` branch anywhere in the path:

```python
root = subject("reference")
rows = declared_rows(DECLARED_ROWS_DOCUMENT, scenario_attributes(root))
markers = declared_markers(rows, scenario_attributes(root))
...
payload = payload_violations(reference_stdout, stdout, markers)
```

`markers` is therefore always `["Kestrelmark Industries", "Volanti Logistics",
"Brightpath Materials", "Cindervale Foods", "Halcyon Textiles",
"Norwind Ceramics"]` — names that exist only in
`runner/scenario-rows.yaml`, which is only ever ingested into a **temporary
copy**, which `--live` skips.

Reproduced against the shipped functions at `7f59289`:

```
$ .venv/bin/python  # drive.py loaded by path, runner dir on sys.path
>>> d.payload_violations(operator_reference_stdout, operator_leg_stdout, markers)
['the leg's stdout carries no declared company name, so it printed a content
  address rather than the Context Product the address names']
>>> d.marker_violations(markers, sorted(d.CONSOLE_VOCABULARY))
[]
```

Consequences, in order of cost:

1. `make example-hw1-harness-clients-live-adk` / `-anthropic` / `-langgraph`
   cannot pass against any deployment except one seeded with exactly this
   document's six rows — i.e. against anything an operator would actually call
   "a real populated deployment". The README documents these targets
   (`README.md:232-236`) and `tests/examples/test_hw1_harness_clients_readme.py::test_the_three_live_targets_exist_and_are_outside_the_always_on_list`
   asserts they exist and are `.PHONY`. Existence is asserted; runnability is
   not, and cannot be — they are never in CI by design.
2. The failure message is **wrong**. It says the leg "printed a content address
   rather than the Context Product", which is false: the leg printed the whole
   product. The runner names the wrong defect, which is precisely the failure
   mode `readme_element_violations` and `porcelain_entries` both go out of their
   way to avoid elsewhere in this phase.
3. `README.md:248-252` tells an adopter to "Point it at your own deployment —
   or run one of the `--live` targets above against a populated one — and
   nothing about the three clients changes". Nothing about the clients does
   change; the *runner* refuses.

Note the adjacency to the `H-09` guards: `driving_call_site_violations` and
`live_leg_coverage_violations` exist to prove `--live` does not fork the code
path. They pass — and the code path being identical is exactly what breaks
`--live`, because the payload gate is unconditional and its data source is the
seed. An AST property over `live` branches structurally cannot see this.

**Fix.** The marker set is a property of the *seeded* subject, so make it one.
Either gate the payload check on the subject actually being seeded, or — better,
because it keeps the check alive under `--live` — derive the markers from the
reference run rather than from the seed document:

```python
# `payload_violations` already treats the reference as the source of truth for
# WHICH names should appear. Under --live the seed document is not that source.
markers = declared_markers(rows, scenario_attributes(root)) if not args.live else None
...
payload = (
    payload_violations(reference_stdout, stdout, markers)
    if markers is not None
    else reference_agreement_violations(reference_stdout, stdout)
)
```

where `reference_agreement_violations` asserts the leg's stdout carries the
company names the reference printed (parsed out of `reference_stdout`), and
refuses a reference that named none — the same vacuity floor
`payload_violations` already carries. Whichever shape is chosen, it needs a
standing control (see `B-3`): a doctored `--live`-shaped pair fed to the same
function, watched passing where it should and failing where it should.

### CR-02: the destination arm's "follows the value to the sink" contract fails for at least eleven spellings, and the `B-2` fix does not close them

**File:** `tools/lints/no_hardcoding.py:531-564` (`resolved_text`),
`:504-528` (`_literal_bindings`), `:582-590` (`instruction_sinks`), against the
contract stated at `:42-45` and `:536-546`.

**Issue.**

`B-2` reports one escape: the destination arm follows only the *positional*
`os.environ.get(...)` default. Measured against the shipped `check_source`, the
hole is much wider, and — this is the part that matters for triage — **a fix
scoped to `B-2` closes only one of these**. All fifteen cases below were run
against the shipped `check_source` at `7f59289` with the same 84-character
prose-candidate literal, so the length floor (`A-1`) is not what is being
measured:

| spelling at the sink | result |
| --- | --- |
| `client.query("<prompt>")` — baseline | FLAGGED |
| `client.query(os.environ.get("X", "<prompt>"))` — CONTROL 6 shape | FLAGGED |
| `client.query(f"<prompt>{x}")` — documented | FLAGGED |
| implicit adjacent concatenation | FLAGGED |
| `p = os.environ.get("X") or "<prompt>"; client.query(p)` | **NOT FLAGGED** |
| `client.query(os.getenv("X") or "<prompt>")` | **NOT FLAGGED** |
| `client.query(textwrap.dedent("<prompt>"))` | **NOT FLAGGED** |
| `client.query("<prompt>".strip())` | **NOT FLAGGED** |
| `client.query("<pro" + "mpt>")` | **NOT FLAGGED** |
| `client.query(x if y else "<prompt>")` | **NOT FLAGGED** |
| `client.query(p := "<prompt>")` | **NOT FLAGGED** |
| `if (p := "<prompt>"): client.query(p)` | **NOT FLAGGED** |
| `p, q = "<prompt>", 1; client.query(p)` | **NOT FLAGGED** |
| `PROMPTS = {"sys": "<prompt>"}; client.query(PROMPTS["sys"])` | **NOT FLAGGED** |
| `client.query(**{"prompt": "<prompt>"})` | **NOT FLAGGED** |
| `args = ["<prompt>"]; client.query(*args)` | **NOT FLAGGED** |
| `client.query(os.environ.setdefault("X", "<prompt>"))` | **NOT FLAGGED** |

Three of these deserve naming individually:

* **`os.environ.get(NAME) or "<prompt>"`.** `_is_environment_read`'s docstring
  (`:484-491`) says the second argument is "a *default*, and a prompt supplied
  as a default is what actually runs on the default path — an env var worn as a
  hat, which is the exact shape ruling 6(a) forbids." The `or` spelling is the
  same hat, is at least as idiomatic, and is an `ast.BoolOp` — so it is not
  reachable by adding keyword handling to `node.args[1]`. **`B-2`'s stated fix
  leaves the shape `B-2` is about still open.**
* **`.strip()` / `dedent()`.** `drive.py:935` in this very phase spells
  `str(conversation["prompt"]).strip()`. The `<literal>.strip()` and
  `textwrap.dedent(<literal>)` forms are how a multi-line prompt is written in
  Python, and both are literals *in the file* — so the docstring's escape hatch
  ("this arm reports literals that are in the file, never values it could not
  see", `:544-545`) does not cover them; they are visible and skipped.
* **`**{...}` and `*args`.** `instruction_sinks` reads `keyword.arg`, which is
  `None` for a splat, and `resolved_text` returns `None` for an `ast.Starred`.
  Both are one-line rewrites of a flagged call.

`_literal_bindings`'s docstring (`:505`) claims "Every ``name = <expr>`` in the
module, at ANY depth, flat." It handles `ast.Assign` with a single `Name` target
and `ast.AnnAssign`, and nothing else — tuple unpacking and `ast.NamedExpr` are
both `name = <expr>` and both missing.

**Fix.** Extend `resolved_text` and `_literal_bindings` to cover the visible-
literal cases, and extend `instruction_sinks` to refuse rather than skip the
opaque ones:

```python
def resolved_text(node, bindings, depth=0):
    ...
    if isinstance(node, ast.NamedExpr):                       # (p := "...")
        return resolved_text(node.value, bindings, depth + 1)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = resolved_text(node.left, bindings, depth + 1) or ""
        right = resolved_text(node.right, bindings, depth + 1) or ""
        return (left + right) or None
    if isinstance(node, ast.BoolOp):                          # env or "<prompt>"
        for value in node.values:                             # the `or` hat
            text = resolved_text(value, bindings, depth + 1)
            if text is not None:
                return text
        return None
    if isinstance(node, ast.IfExp):
        return resolved_text(node.body, bindings, depth + 1) or resolved_text(
            node.orelse, bindings, depth + 1
        )
    if isinstance(node, ast.Call):
        if _is_environment_read(node):
            default = _environment_default(node)               # positional OR keyword
            return None if default is None else resolved_text(default, bindings, depth + 1)
        if _called_name(node.func) in TRANSPARENT_CALLS:       # strip/dedent/lstrip/format
            return resolved_text(node.args[0], bindings, depth + 1) if node.args else None
    return None
```

and in `_literal_bindings`, add `ast.NamedExpr` and the `Tuple`-target form of
`ast.Assign`. For `**{...}` and `*args` the honest answer is a finding rather
than a resolution: a sink call carrying a splat is a call the arm cannot see
into, and reporting it as *unresolvable at a sink* is strictly better than
silence — that is the same posture `client_surface_diff` takes in
`test_hw1_harness_clients_readme.py` for a diff it cannot trust.

Whatever is implemented, the residual paragraph at `:47-54` needs rewriting: it
currently names exactly one residual (a harness whose instruction API uses a
name outside the sink sets) and that is not the residual the tree has.

## Warnings

### WR-01: `model_stub.py` validates only half of a declared exchange, and the unvalidated half answers `500` — the retryable status the module exists to avoid

**File:** `examples/hw1-harness-clients/runner/model_stub.py:218-228`
(`require_paired_exchanges`, the `request:` arm), `:398-420` (`answer_blocks`),
`:302-309` and `:495-500` (`sse`, `stop_reason`), against `:97-105`
(`REFUSAL_STATUS`).

**Issue.** `REDUCTION_KEYS` is documented as "Enumerated so a typo in the
document is a startup error rather than a key that silently never compares"
(`:107-108`), and `require_paired_exchanges` enforces it — for `request:` only:

```python
unknown = sorted(set(exchange["request"]) - set(REDUCTION_KEYS))
```

There is no equivalent for `response:`. `answer_blocks` reads
`declared["blocks"]` and `block["text"]`, and `messages` reads
`exchange["response"]["stop_reason"]` — all unguarded, all inside the route
handler. Measured against the shipped `build_app` through a Starlette
`TestClient`:

| doctored `response:` | startup | first POST |
| --- | --- | --- |
| healthy | accepted | 200 |
| text block missing `text:` | **accepted** | **500** |
| missing `stop_reason:` | **accepted** | **500** |
| missing `blocks:` | **accepted** | **500** |

`REFUSAL_STATUS = 400`'s own comment says why that matters: "a `500` is a
RETRYABLE status to the vendor client sitting behind the CLI: a drifted
conversation there is retried with backoff until the runner's own leg timeout
cuts it off, which turns a precise diagnostic into a 120-second hang and a
`TimeoutExpired`." A typo in the `response:` half produces exactly that, and it
is accepted at startup by the very function written to refuse half-declarations.

**Fix.** Give the response half the same enumerated check, in
`require_paired_exchanges`, before `READY`:

```python
RESPONSE_KEYS: tuple[str, ...] = ("stop_reason", "blocks")
BLOCK_TYPES: tuple[str, ...] = ("text", "tool_use")
...
response = exchange["response"]
missing = [key for key in RESPONSE_KEYS if response.get(key) is None]
if missing:
    print(f"exchange {index} ({exchange.get('name')!r}) declares no {missing}"
          " under 'response:'; a response this stand-in cannot render is a 500"
          " at request time, which the CLI retries until the leg times out",
          file=sys.stderr, flush=True)
    raise SystemExit(1)
for block in response["blocks"]:
    if block.get("type") not in BLOCK_TYPES:
        ...refuse...
    if block["type"] == "text" and not block.get("text"):
        ...refuse...
```

Wrap `messages` in a `try/except (KeyError, TypeError)` returning `refuse(...)`
as the floor beneath it, so a shape the startup check has not learned still
arrives as a `4xx` rather than as a hang.

### WR-02: the README claims the no-model guard requires the *reference* content address; the test requires only that the two guarded legs agree with each other

**File:** `examples/hw1-harness-clients/README.md:187-192`, against
`tests/examples/test_hw1_harness_clients_no_model.py:288-311`.

**Issue.** The README says:

> `tests/examples/test_hw1_harness_clients_no_model.py::install_no_model_guard`
> patches name resolution and socket connection to refuse, drives both clients
> in-process behind the guard, and **requires them to still print the reference
> content address.**

The test's only address assertions are:

```python
assert sorted(addresses) == sorted(GUARDED_LEGS), addresses
assert len(set(addresses.values())) == 1, (...)
```

`reference_run` is never called in that module and no reference address is
computed. "The reference content address" has a precise meaning in this example
— `drive.py::reference_run`'s `consume.py` answer, criterion 4's operand — and
the guarded legs are compared to each other, not to it.

This is **not** rejected finding `R-3`. `R-3` was rejected because the sentence
codex quoted did not exist in the *test module's* docstring; the panel noted in
the same breath that "the substantive observation — that this module compares
the two guarded legs to each other, not to `consume.py` — is true, but it is not
an overclaim." It becomes one here, in the README, in the sentence quoted above.

**Fix.** One word:

```diff
-in-process behind the guard, and requires them to still print the reference
-content address.
+in-process behind the guard, and requires them to still print the same content
+address as each other. Criterion 4's comparison against the reference is
+`drive.py::compare_addresses`, exercised by `make examples`.
```

### WR-03: CINV-01c's "every *static* rename is covered" is false for three one-line renames

**File:** `tools/lints/no_hardcoding.py:740-747` (the claim), `:751-776` (the
alias collector).

**Issue.** The comment states: "Every *static* rename is covered; dynamic
construction … stays the D-12 accepted residual, which is the whole point of the
distinction — a one-line static rename must not escape." Measured against the
shipped `check_source` for `src/ccf/x.py`:

| rename | result |
| --- | --- |
| `a = Agent("x")` | FLAGGED |
| `A = Agent; a = A("x")` | FLAGGED |
| `a = mod.Agent("x")` | FLAGGED |
| `from ccf.agents import Agent as A; a = A("x")` | FLAGGED |
| `A: type = Agent` then `A("x")` | **NOT FLAGGED** |
| `A, B = Agent, Task` then `A("x")` | **NOT FLAGGED** |
| `a = (A := Agent)("x")` | **NOT FLAGGED** |

All three are one-line, static, and visible in the AST. The asymmetry is inside
this one file: `_literal_bindings` (`:522-527`) *does* handle `ast.AnnAssign`;
the CINV-01c collector matches `ast.Assign` only. Two binding collectors, two
different node coverages, one module.

**Fix.** Reuse one collector, or at minimum widen the CINV-01c walk:

```python
for node in ast.walk(tree):
    aliased: ast.expr | None = None
    targets: list[ast.expr] = []
    if isinstance(node, ast.Assign):
        aliased, targets = node.value, list(node.targets)
    elif isinstance(node, ast.AnnAssign) and node.value is not None:
        aliased, targets = node.value, [node.target]
    elif isinstance(node, ast.NamedExpr):
        aliased, targets = node.value, [node.target]
    # ... plus Tuple-target/Tuple-value zipping for `A, B = Agent, Task`
```

Then correct the "every static rename" sentence to match what ships, and add a
control per newly-covered shape beside `test_agent_construction_outside_a_factory_is_flagged`.

### WR-04: the retirement gate never asserts the retired client programs survived the move, although its own violation text and its README say the move preserves them

**File:** `tests/examples/test_hw1_harness_clients_retirement.py:107-153`
(`retirement_violations`), `:397-404` (`_retired_tree`), against
`docs/retired/16-external-consumers/README.md:29-47`.

**Issue.** `retirement_violations` checks three things: the condemned directory
is gone, the retired root is a directory, and it holds a `README.md`. It never
checks that `client_langgraph.py` and `client_claude_agent.py` are there —
though its own violation message asserts the reason they must be:

```python
f"{retired_root} is missing, so the condemned material has no"
" declared destination. `H-13` is a move, not a deletion: the two"
" client programs carry shapes Phase 20 inherited"
```

The control fixture writes one of them into the synthetic tree
(`(retired / LANGGRAPH_CLIENT_NAME).write_text("")`) and asserts nothing about
it. So the gate is satisfied by an empty directory with a README — a *deletion*
plus a record, which is precisely the state the retired README's "Why it is here
rather than deleted" section argues against.

Contrast `historical_example_violations` in the same module, which asserts the
`H-14` side **positively** and explains why: "without it this module would only
ever push toward deleting things". The `H-13` side has no such arm.

Mitigating, and worth recording so this is not over-graded: `cite03-node-id` in
`tools/lints/citations.py` currently protects both files, because
`SECTION-2-TRANSPORT.md:24` cites
`docs/retired/16-external-consumers/client_langgraph.py::build_graph` and the
retired README cites `client_claude_agent.py::session_options`. That protection
is incidental — it disappears the day either citation is reworded.

**Fix.** Mirror the `H-14` arm:

```python
#: The two programs `H-13` moves rather than deletes.
RETIRED_CLIENT_NAMES = ("client_langgraph.py", "client_claude_agent.py")
...
violations += [
    f"{retired_root / name} is missing. `H-13` is a MOVE: the retired"
    " directory exists to hold the two client programs, and a record-only"
    " directory is the deletion the retirement record argues against"
    for name in RETIRED_CLIENT_NAMES
    if not (retired_root / name).is_file()
]
```

plus a control that removes one from `_retired_tree` and watches it fire.

### WR-05: the no-model gate re-spells two of `drive.py`'s constants in a module that already imports the runner

**File:** `tests/examples/test_hw1_harness_clients_no_model.py:126`
(`CONTENT_ADDRESS_RE`), `:214-216` (`client_program`), against
`examples/hw1-harness-clients/runner/drive.py:227` (`_CONTENT_ADDRESS_RE`),
`:147` (`CLIENT_PREFIX`), `:302-304` (`client_program`).

**Issue.** The module calls `load_runner()` and uses `drive.seeded_subject`,
`drive.resolve_door`, `drive.build_question`, `drive.AS_OF` and
`drive.known_legs()` — then re-declares two facts the same module already owns:

```python
CONTENT_ADDRESS_RE = re.compile(r"content address\s+([0-9a-f]{64})")   # test
_CONTENT_ADDRESS_RE = re.compile(r"content address\s+([0-9a-f]{64})")  # drive.py

def client_program(leg): return EXAMPLE_ROOT / f"client_{leg}.py"      # test
def client_program(leg): return EXAMPLE_ROOT / f"{CLIENT_PREFIX}{leg}.py"  # drive.py
```

The `client_` prefix is spelled as a literal here, defeating `CLIENT_PREFIX`'s
stated purpose ("adding a harness is adding a file"). Today the drift fails
loud — `test_the_guarded_client_programs_exist` catches a prefix change — but
this is exactly the "two source-of-truth lists that can drift apart" shape, and
the module has the import already.

**Fix.** `drive = load_runner()` at module scope is already the pattern; use
`drive._CONTENT_ADDRESS_RE` (or promote it to a public name in `drive.py`) and
`drive.client_program`.

### WR-06: the one-token claim computes the differing position and then discards it, matching on `[-1]` instead

**File:** `tests/examples/test_client_example_purity.py:592-619`
(`test_the_three_harness_commands_differ_in_exactly_one_token`), against
`:552-566` (`single_token_difference_violations`).

**Issue.** `single_token_difference_violations` does the work properly — it
computes `differing`, refuses unless `len(differing) == 1`, and reads
`tokens[differing[0]]`. The test then throws that away:

```python
violations = single_token_difference_violations(commands)
assert not violations, "\n".join(violations)

differing = {shlex.split(command)[-1] for command in commands}
```

Two notions of "the differing token" in eight lines: one derived, one assumed to
be the last position. The two agree only because the README's commands happen to
end with the leg name. Add `--live` to all three documented commands and the
derived answer stays correct while `[-1]` returns `{"--live"}`; the assertion
then goes red naming "legs the example does not ship", which is a misdiagnosis
of a README the gate should have accepted.

**Fix.** Return the differing values from the checker, or recompute them the
same way:

```python
token_lists = [shlex.split(command) for command in commands]
position = next(
    index for index in range(len(token_lists[0]))
    if len({tokens[index] for tokens in token_lists}) != 1
)
differing = {tokens[position] for tokens in token_lists}
```

### WR-07: `experience.yaml`'s own [MECHANISM]/[ADAPT] key enumeration was not updated for the key this phase added

**File:** `examples/external/00-hello-context/artifacts/experience.yaml:21-24`,
against `:125` and `examples/external/00-hello-context/run.py:663`.

**Issue.** The document's header enumerates its own contract:

> In this file: `class_id`, `server_name`, issuer/resource URLs, scope names,
> tool prose, model names and allowlisted tool names are [ADAPT]; the keys
> `semver`, `class_id`, `declaration`, `auth`, `tools`, `tool_allowlist`,
> `agent_exposure` and `live_mode` and their inner field names are [MECHANISM].

`client_question` is neither list. It *is* mechanism — `run.py` reads it by
exact name (`experience["client_question"]`) and a rename is a `KeyError` — and
the new comment block correctly marks its *value* `[ADAPT]`, but the header's
enumeration is now an incomplete statement of the document's own contract. The
same header is the thing an adopter reads to know what they may rename.

**Fix.** Add `client_question` to the `[MECHANISM]` key list at `:23-24`.

### WR-08: this phase made three client filenames ambiguous basenames, and the citation gate drops ambiguous citations silently

**Files:** `examples/hw1-harness-clients/client_{adk,anthropic,langgraph}.py`,
`examples/external/00-hello-context/client_{adk,anthropic}.py`,
`docs/retired/16-external-consumers/client_langgraph.py`, against
`tools/lints/citations.py`'s stated blind spot ("A bare `run.py:NNN` naming one
of eleven `run.py` files … is counted as *unchecked* and is never a finding").

**Issue.** Measured with the shipped `citations.repo_index`:

```
client_adk.py       ['examples/hw1-harness-clients/client_adk.py',
                     'examples/external/00-hello-context/client_adk.py']
client_anthropic.py ['examples/hw1-harness-clients/client_anthropic.py',
                     'examples/external/00-hello-context/client_anthropic.py']
client_langgraph.py ['examples/hw1-harness-clients/client_langgraph.py',
                     'docs/retired/16-external-consumers/client_langgraph.py']
```

All three became two-valued in this phase — the first two by `H-14`'s mandated
duplication, the third by `H-13`'s move. Any future citation spelled
`client_adk.py:142` or `client_adk.py::report` is now silently **unchecked**
rather than resolved, and `--report` counts it under "UNCHECKED — path
ambiguous" (currently 15 tree-wide).

**Latent, not live.** Every current reference to these names is either a
full-path citation (`examples/hw1-harness-clients/client_langgraph.py::build_graph`)
or bare prose in backticks with no `:NNN`/`::symbol`, so nothing is being dropped
today. Verified by grep across `docs/`, `public/`, `examples/` and `tests/`.

**Fix.** No code change needed. Record the constraint where the duplication is
mandated — `tests/examples/test_hw1_harness_clients_retirement.py`'s
`test_two_of_these_names_under_examples_is_the_mandated_state` is the natural
home — so the next author citing one of these files knows a bare basename buys
nothing:

```python
"""...
Consequence for `tools/lints/citations.py`: these basenames are AMBIGUOUS, and
an ambiguous path is dropped from the citation sweep rather than checked. Cite
these three files by FULL PATH, always.
"""
```

### WR-09: the deferral-marker gate indexes `[0]` on every artifact document's lines

**File:** `tests/examples/test_artifact_schema_headers.py:544-551`.

**Issue.**

```python
if path.read_text(encoding="utf-8").splitlines()[0].startswith(DEFERRED_PREFIX)
```

An empty (or whitespace-only-with-no-newline) `artifacts/*.yaml` raises
`IndexError` here rather than being reported as an unheadered artifact. The
module's own controls create exactly that shape —
`(stray / "x.yaml").write_text("")` at `:381` and `:406` — under `tmp_path`,
where `_artifact_documents()` does not reach, so the branch is unexercised. The
failure would surface as a collection-time `IndexError` in a coverage gate,
which is the "reports the wrong defect" mode this module argues against
elsewhere.

**Fix.**

```python
lines = path.read_text(encoding="utf-8").splitlines()
if lines and lines[0].startswith(DEFERRED_PREFIX)
```

and let `check_directory` report the empty document as the missing-header
finding it is.

---

## What was checked and found sound

Recorded because it is load-bearing for triage — these are the surfaces a second
adversarial read did *not* break:

- **The purity gate** (`test_client_example_purity.py`). `_covers` is one
  function shared by the permitted test and the refusal test, precisely so "two
  different notions of *under*" cannot arise — the symmetry `B-1` lacks.
  `C-20-5` is a genuine per-root control that a module-level union would fail.
  Both vacuity cases and all four import shapes are exercised against
  `tmp_path` copies fed to the shipped function.
- **The README element gate**. `_flat` is applied to **both** the README text
  and each marker before comparison (`:184`, `:192`) — symmetric normalization,
  and the counter-example to `B-1`.
- **Criterion 7's diff assertions**. `client_surface_diff` refuses an empty
  base, an empty path list and a non-zero `git` exit, and `CONTROL 6` watches it
  produce output for a tree that demonstrably changed. This is the strongest
  anti-vacuity design in the file set.
- **The socket guard's in-situ arming probe** (`assert_guard_is_armed`), and
  `CONTROL 1`'s rewrite to distinguish a whole guard from half a guard.
- **`phony_declarations`**' continuation-line handling, with the measured note
  about why the naive version produced "a confident, specific, wrong finding".
- **Harness neutrality and No-Hardcoding across the three clients.** Zero `ccf`
  imports (AST-verified by the shipped gate); no prompt literal in any client;
  leg 2 subscripts `CCF_HARNESS_PROMPT` rather than defaulting it; the external
  example's two `os.environ.get(..., "<prompt>")` fallbacks were correctly
  converted to required reads with the text moved into
  `artifacts/experience.yaml`. No example in scope would run meaningfully with
  its artifacts deleted.
- **The README's `request`-argument arithmetic.** "Eight required arguments,
  seven self-describing plus `request`" checks out against
  `runtime/ccf_runtime/mcp/egress.py:534-543`: the tool takes nine parameters and
  `parameters` carries a default, so eight are `required` in the schema.
  (Checked because `src/ccf/client/adapters/mcp_stdio.py:47` says "nine
  arguments" and the two read as contradictory; they are not.)

---

_Reviewed: 2026-08-21_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
_Additive to: `20-CLOSE-REVIEWS.md` (cross-AI panel). No finding above restates B-1, B-2, B-3, A-1..A-4, or resurrects R-1..R-4._
