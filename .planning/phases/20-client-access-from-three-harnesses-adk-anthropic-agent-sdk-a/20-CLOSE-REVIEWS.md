---
phase: 20
kind: close-review
subject: shipped code
reviewers: [gemini, codex, cursor]
reviewed_at: 2026-08-21T06:20:00-07:00
self_reviewer_skipped: claude (executing model — §3.1 independence)
base: 9e4bd0e5c54c22133f32c108b96de3aebbf6dfae..HEAD
source_inlined: 5889 lines / 304 KB (3 clients, runner/drive.py, runner/model_stub.py,
  question.yaml, model-conversation.yaml, README.md, tools/lints/no_hardcoding.py,
  test_client_example_purity.py, test_hw1_harness_clients_no_model.py)
---

# Cross-AI CLOSE Review — Phase 20 (SHIPPED CODE)

Distinct from the pre-execution plan reviews (four rounds, 11 → 7 → 4 → 0), which
survive in their own files. This panel read the **committed tree**, was handed the
phase's three known defect classes, and was told not to re-derive them.

**Every finding below was verified against the tree before being recorded.** Three
were confirmed by running the shipped code against doctored inputs; three were
confirmed by reading; **four were rejected** and are recorded as rejected.

## Verified BLOCKING findings

### B-1 — `marker_violations` matches words, `observed_markers` matches substrings, so an address-only leg passes the check written to refuse it

`examples/hw1-harness-clients/runner/drive.py:437` (property 4),
`:453` (`observed_markers`), `:256-280` (`CONSOLE_VOCABULARY`).

Origin: cursor M2 (`product` case). **Generalized and proven** during verification.

`payload_violations` exists for exactly one purpose, stated in its own docstring:
refuse "a client that printed its address and nothing else … and **CONTROL A** is
the doctored stdout that is exactly its shape." Property 4 of `marker_violations`
is what keeps a declared name from being satisfiable by chrome. It compares the
**whole lowercased words** of the name against the vocabulary:

```python
collisions = sorted(word for word in _words(name) if word in chrome)
```

but `observed_markers` matches by **raw substring**:

```python
return [name for name in declared_names if name in stdout]
```

Two independent escapes follow, and both were run against the shipped functions:

| declared `name` | `marker_violations` | address-only leg vs `payload_violations` |
| --- | --- | --- |
| `product` | accepted | **PASSED** — the gate does not fire |
| `text` | accepted | **PASSED** |
| `ntex` | accepted | **PASSED** |
| `Kestrelmark Industries` (current) | accepted | CAUGHT — correct |

- `text` / `ntex` are **substrings of the chrome word `context`**. Property 4 never
  sees them because they are not equal to a chrome word.
- `product` is worse: the three clients all print the literal line
  `print("context product")` (`client_adk.py:142`, `client_langgraph.py:219`,
  `client_anthropic.py:215`), and `product` **is not in `CONSOLE_VOCABULARY` at
  all**. The vocabulary was sourced from `consume.py::main` plus the runner's own
  output — but the check greps the **leg's** stdout, which prints a word neither
  source contains. The guard was assembled from the wrong output stream.

Failure scenario: a future edit renames a row in `runner/scenario-rows.yaml` to a
name that is a substring of leg chrome. `marker_violations` stays green. A leg that
regresses to printing its address and the label line — CONTROL A's exact subject —
now satisfies `payload_violations`, and Success Criteria 1-3 are asserted by a check
that cannot fail. This is the phase's own defect class **(a)**, latent rather than
live: the six current names are safe.

Reproduction: `marker_violations([name, "Volanti Logistics"], sorted(CONSOLE_VOCABULARY))`
and `payload_violations(reference_stdout_naming_that_row, "content address <64 hex>\ncontext product\n", [name])`.

### B-2 — the CINV-01a destination arm follows only the positional env default, so `default=` as a keyword escapes it

`tools/lints/no_hardcoding.py:561-563`, against the intent stated at `:484-491`.

Origin: cursor H2. Confirmed by running `check_source` on six fixtures.

```python
if isinstance(node, ast.Call):
    if _is_environment_read(node) and len(node.args) >= 2:
        return resolved_text(node.args[1], bindings, depth + 1)
return None
```

`_is_environment_read`'s docstring names the shape the arm was minted for: "a prompt
supplied as a default is what actually runs on the default path — **an env var worn
as a hat**, which is the exact shape ruling 6(a) forbids." The resolution reads
`node.args[1]` only, so a keyword default leaves `len(node.args) == 1` and
`resolved_text` returns `None`.

Measured against the shipped `check_source`:

| fixture | result |
| --- | --- |
| long literal direct at `client.query(...)` | FLAGGED |
| `os.environ.get("CCF_HARNESS_PROMPT", "<long prompt>")` — CONTROL 6's spelling | FLAGGED |
| `os.environ.get("CCF_HARNESS_PROMPT", default="<long prompt>")` | **NOT FLAGGED** |
| `os.getenv("CCF_HARNESS_PROMPT", default="<long prompt>")` | **NOT FLAGGED** |

Both keyword spellings are valid Python and were executed to confirm it:
`os.environ.get(k, default=d)` and `os.getenv(k, default=d)` both return `'D'`.
`os._Environ` inherits `get` from `collections.abc.Mapping`, a Python `def`, so the
keyword is accepted; `os.getenv` is likewise a Python `def`.

`tools/lints/tests/test_no_hardcoding.py` exercises only the positional form
(CONTROL 6). The arm covers one spelling of the one shape ruling 6(b) minted it to
refuse — defect class **(b)**, a check narrower than the claim it is named for.

### B-3 — the three runner checks carrying Criteria 1-4 have no standing sabotage control

`drive.py:384` (`marker_violations`), `:458` (`payload_violations`),
`:808` (`compare_addresses`); called at `:1064`, `:1098`, `:1106`.

Origin: cursor H1. Confirmed by repo-wide grep: these three symbols appear **only**
inside `drive.py`. No test imports, calls or probes them.

Their controls (CONTROL A-F) were run as one-shot mutation probes during plan 20-03
and recorded in `20-03-SUMMARY.md:164-172` as a RED→GREEN table — evidence that they
*could* fail on the day, not a watcher that keeps them able to fail. Contrast the
purity gate (`test_client_example_purity.py`, controls C-20-1..C-20-9) and the
no-model guard (`test_hw1_harness_clients_no_model.py`, CONTROL 1-3), both of which
ship standing pytest controls.

This is the phase's inherited `CLNT-12` standard — *every new gate carries a named
sabotage control in the same plan that adds it* — discharged by a SUMMARY table
rather than by a test. **B-1 is the direct consequence**: the escape it describes is
one a standing control over `marker_violations` would have been positioned to catch.
Whether a recorded one-shot probe discharges `CLNT-12` is a ruling for Dave.

## Verified ADVISORY findings

### A-1 — the destination arm's finding message claims length-independence the code does not have

`tools/lints/no_hardcoding.py:691`. Raised by all three reviewers (gemini #1 HIGH,
codex HIGH, cursor M3 MEDIUM) — the only three-way consensus in the panel.

The emitted message reads: "a prompt is refused by where it goes, **not by how long
it is**". The arm calls `_is_prose_candidate` at `:686`, which floors at
`MIN_PROMPT_CHARS = 40` (`:108`, `:377`). Measured on the shipped `check_source`:
`client.query("Call the tool once, then stop.")` and
`LlmAgent(instruction="Call the tool once.")` are **NOT FLAGGED**.

The *coverage* limit is not a defect: `:677-680` records 40 as the measured knee
(40→2, 20→2, 12→15, 1→17 findings) and CONTROL 8 at
`tools/lints/tests/test_no_hardcoding.py:429-446` pins it deliberately. It is
documented, not a silent narrowing. What is wrong is the **sentence**: a reader who
believes it will conclude a short hardcoded instruction is refused when it is not.
Advisory because the fix is prose, and the ruling that set the floor stands.

### A-2 — `model_stub.py`'s `seen` is written and never read, which its own docstring calls the pattern this project refuses

`examples/hw1-harness-clients/runner/model_stub.py:427` (parameter), `:467`, `:505`
(appends), `:545` (initialisation). Raised by gemini #2. Confirmed: grep shows
append and pass-through only, no read, no return, no print.

The module docstring at `:45` says, of what it deliberately did not copy from
the 00-hello-context replay server: "a member nothing reads is the `C-10` pattern
this project refuses." `seen` is one. No behavioural impact; it is the module's own
stated standard applied to itself.

### A-3 — `reference_run`'s subprocess has no timeout while the leg's does

`drive.py:765` versus `:991`. Raised by gemini #3. Confirmed: `drive_leg` passes
`timeout=LEG_TIMEOUT_SECONDS`; `reference_run`'s `subprocess.run` passes none. A
hung `consume.py` hangs CI without a diagnostic. Low likelihood, cheap fix.

### A-4 — a leg timeout leaves the door grandchild unreaped

`drive.py:991`, against the reasoning at `:966-971`. Raised by cursor L1. Confirmed
as described — and confirmed as **already documented**: the docstring states the
door "is spawned by the client's own harness library (`H-01`), one process further
down than this runner can see." In practice a stdio door exits on stdin EOF when its
parent dies. Recorded for completeness, not action.

## REJECTED findings

Recorded as rejected per the close briefing. An unverified finding acted on is worse
than no review.

### R-1 — gemini #4: `marker_violations` word-collision check is case-sensitive

**Rejected — the scenario is backwards.** gemini claims a company named `CONtEXT`
would evade the check. `_words` (`drive.py:292`) lowercases every token
(`match.group(0).lower()`), so `_words("CONtEXT") == ["context"]`, which **is** in
`CONSOLE_VOCABULARY`, and the collision fires correctly. The residual point — that
`chrome_words` is not defensively lowercased for a hypothetical future
non-lowercase vocabulary — is a nit, not the reported defect. (The *real* defect in
this function is B-1, which gemini did not find.)

### R-2 — codex #2: payload gate can pass without the client printing the Context Product

**Rejected as stated — the scenario is the gate passing for the right reason.**
codex's leg prints `Acme Corp` and `Halcyon Revenue`, i.e. the declared company
names, which is precisely the evidence `payload_violations` is designed to require;
the absence of the literal label `context product` is not what the check tests.
codex was directionally right that this gate is the soft spot, but its concrete
scenario does not fail. **Superseded by B-1**, which is the version that does.

### R-3 — codex #3: the no-model test overclaims a reference-address proof

**Rejected — the quoted docstring sentence does not exist.** codex asserts the
module docstring says the guard "requires them to still print the reference content
address." `grep -n "reference" tests/examples/test_hw1_harness_clients_no_model.py`
returns **nothing**. The test's actual docstring (`:281-291`) says the legs "must
print the **same** content address", which is exactly and only what it asserts
(`:309`). The substantive observation — that this module compares the two
guarded legs to each other, not to `consume.py` — is true, but it is not an
overclaim: Criterion 4 is carried by `compare_addresses` in the runner, exercised by
`make examples`. This is the fabricated-citation failure mode this project has
rejected reviewer output for before. (cursor M1 raised the same scope observation
without the false quote and is accurate; it is not a defect either.)

### R-4 — the three reviewers' clean bills on the purity and no-model gates

Not a finding, recorded because it is load-bearing: all three panelists examined
`test_client_example_purity.py` and `test_hw1_harness_clients_no_model.py` and
independently reported the AST purity gate, its C-20-* controls, the process-global
socket guard and its in-situ arming probe as sound and sabotage-capable. Criterion 5
and Criterion 6's default-path half are the best-defended surfaces in the phase.

## Consensus

**Agreed strengths** (2+ reviewers): the AST purity gate and its standing controls;
the socket-refusal guard with an arming probe inside the same context the legs run
in; leg 2's fail-loud stand-in and its `ANTHROPIC_BASE_URL` refusal; criterion 7's
diff assertion with vacuity controls on an empty base and empty path set; the
retirement of the prior-vintage duplicates.

**Agreed concerns** (2+ reviewers): the `MIN_PROMPT_CHARS = 40` floor on the
destination arm (all three — A-1); the payload/marker surface being the least
defended part of the runner (codex and cursor, from different angles — B-1).

**Divergent:** codex read the runner's payload gate as structurally overclaiming and
cursor read it as under-controlled. Verification says cursor was right about the
mechanism and codex was right about the location. B-1 is the finding neither stated
in full.

## Panel reliability, this host

- **gemini** — 4 findings, 3 verified (2 advisory, 1 nit), 1 rejected for a
  backwards scenario. No fabricated symbols this round, but R-1 shows the pattern
  the standing note warns about: confident reasoning over code it half-read.
- **codex** — read the inlined source (real line numbers, real quotes, 95,655
  tokens). 3 HIGH claimed, 1 verified as a duplicate of the consensus advisory, 1
  rejected as a passing scenario, 1 rejected for a **fabricated docstring quote**.
  The sandbox-reads-nothing failure did not recur with source inlined.
- **cursor** — 4m24s, the strongest pass: both surviving BLOCKING findings (B-2,
  B-3) and the seed of the third (B-1) came from it, with accurate `path:line`
  citations throughout and a correctly-hedged severity on the consensus item.
