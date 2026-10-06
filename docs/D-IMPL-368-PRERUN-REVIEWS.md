# D-IMPL-368 — the PRE-RUN panel on the two companion documents

**Subject:** `docs/superpowers/specs/2026-10-05-remaining-rows-exploit-tests.md` and
`docs/superpowers/specs/2026-10-05-remaining-rows-rulings-batch.md` as merged to `main` @ `933ef91f`,
inlined in full in one prompt (36,461 bytes) with the bank context, the known findings and the
output rules. **Reviewers:** Codex (`codex exec`), Cursor (`cursor agent -p --mode ask`), Fable
(an independent Fable agent with read-only tree access). **Executor:** excluded. **Date:** 2026-10-05.
**Verifier:** every tree claim below was checked by the orchestrator against `933ef91f` before it
was accepted; the verification column says what was run.

## Seat reliability

| Seat | Read the tree? | Output | Counted as a reviewer? |
| --- | --- | --- | --- |
| Codex | **No** — every shell command failed (`bwrap: loopback: Failed RTM_NEWADDR`); it said so explicitly and labeled all tree statements as inferred | 8 findings, 28,371 tokens, every citation a document section | **Yes, as a document reviewer only**; its tree claims were not relied on |
| Cursor | Yes — cited 14 symbols; `.git/HEAD` unreadable so the base SHA was unverified by it | 10 findings | Yes; its four tree claims that mattered were re-verified (below) |
| Fable | Yes, with two measured probes (a throwaway Makefile; a pydantic/pytest probe) | 13 findings F-01…F-13 | Yes |

## Findings on the three PILOT rows, with disposition

| # | Seat(s) | Finding | Verified how | Disposition |
| --- | --- | --- | --- | --- |
| P1 | Codex 5, Cursor 1, Fable F-01/F-03 | SEC-014's severing "drop the mode on the file open" names an API the store does not use (`write_bytes`/`mkdir`); a `umask`-only fix or a directory-less fix passes; `tmp_path` is already `0o700` so the directory assertion is vacuous; a pre-existing root never gets a mode from `mkdir(exist_ok=True)` | `grep` of `file_store.py` (no `open(`); pytest `tmpdir` mode read by the Fable seat | **ACCEPTED, BLOCKING.** Row rewritten: store created at a non-existent nested root; pre-existing root **tightened** to `0o700` (the Q8 "fixed modes" reading; Dave may prefer refuse-by-name, flagged in the pilot report); modes set explicitly after creation; three severings (files, directories, root tightening); umask-only fix declared non-conforming |
| P2 | Fable F-04 | `products/product.py::open_product` creates the root's parents wide, outside the row's surface | not re-verified (outside the pilot) | **CARRIED** as a SEC-014 follow-on finding |
| P3 | Codex 1, Fable F-05 | SEC-024's "absent from every record" is green on the unfixed tree if read as record messages: `_opaque_failure` logs a constant message; the canary is only in the rendered traceback | `sed` of `egress.py::_opaque_failure` | **ACCEPTED, BLOCKING.** Assertion surface fixed: `caplog.text` and `Formatter().format(record)` at the root logger |
| P4 | Fable F-06 | The door's own `ValueError` f-strings embed `parameters`, `product_id`, path segments; `hide_input_in_errors` does not touch them; the described test is green after the pydantic fix while caller values still reach the log | `grep` of `egress.py` for `!r}` f-strings (Fable); accepted on its inspection | **ACCEPTED, BLOCKING.** Row rewritten with three cases and three severings; fix shape: `_opaque_failure` renders type names and frames only for the whole chain, and the four message sites carry keys and locations, never values |
| P5 | Codex 2, Cursor 3, Fable F-07/F-08 | The egress case was underspecified; one severing for two cases; `.errors()` still carries input after the pydantic flag; wire shape must stay opaque | Fable measured `.errors()` on pydantic 2.12.5 | **ACCEPTED.** Folded into P3/P4; wire-shape assertion added as the regression guard |
| P6 | Codex 3, Fable F-10 | SEC-026's `?=` rule used the literal `://user:pass@`, which does not match line 295 | read of the document; `grep` of `Makefile` line 295 | **ACCEPTED, BLOCKING.** Userinfo regex with positive and negative control fixtures; the default is deleted and `leg-neo4j` refuses by name when unset; `ci.yml` sets the URI in job `env` (Fable inspected) |
| P7 | Cursor 2, Fable F-09 | The "six lines" list was wrong both ways: line 306 echoes the DSN through `$(PG_DSN_ENV)` (name ends `_ENV`, a suffix rule misses it); lines 318/339/341 expand `CCF_TEST_FLUREE_URL` and were omitted | `grep` of `Makefile` recipe lines: 306, 310, 314, 318, 339, 341, 367, 369 + default 295 | **ACCEPTED, BLOCKING.** "Today" restated to the measured eight plus the default; the lint resolves one level of indirection; `URL` in scope by name |
| P8 | Fable F-11, Codex 4 | The lint was a proxy uncoupled from make: `@` is effective only on the **joined logical line** (all eight are backslash-continued); `make -n` prints `@` lines so a dry run cannot go green; no behavioral test; `echo`/`printf`/`set -x` behind `@` still leak | Fable measured both with a throwaway Makefile | **ACCEPTED, BLOCKING.** A behavioral exploit test (`make <target> SHELL=/bin/true` with a CANARY DSN in the environment, assert absence from stdout+stderr) is now the primary test and the "remove one `@`" severing reddens it directly; the lint works over joined logical lines and refuses `echo`/`printf`/`set -x` |
| P9 | Codex 8, Cursor 4 | Q20's option text said "four conditions"; §0 defines three | read of both documents | **ACCEPTED.** Q20 says three |
| P10 | Fable F-12 | Condition 3 (no regression) had no measured baseline | — | **ACCEPTED.** The executor measures the named suites on the base SHA before any change and records the counts |
| P11 | Fable F-13 | Say which target proves `tools/lints/tests` | — | **ACCEPTED** in the executor brief (`make gate-tools` runs them; run the directory directly as well, per CLAUDE.md §3.1) |

## Findings on NON-pilot rows (document corrections only; no row executes under the pilot)

| # | Seat(s) | Finding | Verified how | Disposition |
| --- | --- | --- | --- | --- |
| N1 | Cursor 5 | **SEC-017's "Today" is false:** the three tools are already tenant-guarded (`tenancy.py::_select_tenant` raises `CrossTenantRefused`; `tests/mcp/test_tenant_guard.py::test_the_three_agent_and_replay_tools_are_tenant_guarded`); the open pin `tests/crossproc/test_experience_edge.py::test_the_agent_and_replay_tools_are_authenticated_but_not_entitled_open_gap` is about **product entitlement within a tenant** | `grep` of all three symbols on `933ef91f` | **ACCEPTED, ESCALATED.** Q10's premise is false on the tree. Not executed. Dave rules: close SEC-017 on the existing tenant evidence (product entitlement stays under `D-IMPL-129`) or redefine the row to the product-entitlement gap |
| N2 | Cursor 6 | SEC-015's lint accepted any `permissions:` block, including `write-all` | read of the document | **ACCEPTED.** Restrictive block required; top-level `write` refused |
| N3 | Cursor 7 | SEC-021's "LF parses before the size check" is wrong today: `lf_a2a.py::LfA2AWire._accept` calls `_carried_bytes` (size refusal) before `model_validate_json` | `sed` of `_accept` | **ACCEPTED.** Case (b) marked already-held on the LF leg; retained only if the executor names a path that still parses first |
| N4 | Cursor 8 | SEC-019 said "four tests" and "three cases" | `git grep required-absent -- tests` (four assertions, three files) | **ACCEPTED.** Four node ids to be listed by name |
| N5 | Cursor 9, Codex 6 | SEC-025's "Today" overstated: the `mcp-product` leg already binds the question echo (`D-IMPL-340`/`342`); local dispatch is the unbound leg; the test needs one mismatch subcase per leg | `grep` of `composite.py` | **ACCEPTED.** "Today" refined; three subcases; two severings |
| N6 | Codex 7 | SEC-028's wording would force `--require-hashes` onto the editable install | read | **ACCEPTED.** Lock installs `--require-hashes`; editable install `--no-deps` |
| N7 | Cursor 10, Fable §F | Missing regression guards: SEC-022 (peering examples, admitted-product behavior), SEC-013 (in-process semantics unchanged; SQLite lease an OS lock, not an existence check), SEC-020 (control the address guard for estate drift) | — | **ACCEPTED.** Added to each row |

## Rejected

None. Every finding resolved against the tree or against the documents' own text.

## What the panel did not find

No ruling contradicts another ruling or a stated invariant for the pilot rows (all three seats).
The `D-IMPL-368` overrides match the documents (Fable). Nothing in the three pilot rows required a
new design choice beyond Q8's pre-existing-root reading, which is recorded above and flagged for
Dave in the pilot report rather than escalated as a blocker, because both readings are inside
"fixed modes, no knob" and the row's test pins whichever is ruled.
