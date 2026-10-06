# The remaining security rows: every ruling the run needs, asked once

**Status: PROPOSED, awaiting Dave's rulings.** Date: 2026-10-05. Base: `main` @ `1f6179c5`.
Companion: `2026-10-05-remaining-rows-exploit-tests.md` (the definition of done per row).
Next free decision id: `D-IMPL-368` (reserved for the entry that records these rulings).

## 0. What this is

Twenty questions. Each has the options, the consequence of each, and a recommendation. Every one
is a decision an unattended run would otherwise either stall on or make without Dave. The intent is
that after this batch is ruled, nothing in the twelve-row run needs a new ruling; anything that
turns out to need one is **parked by the executor, not decided**, and the row stops at that point.

Nothing here reopens an axis locked by `D-IMPL-356` or `D-IMPL-367`.

## 1. Process rulings

### Q1 — Panel cadence for the mediums

`D-IMPL-352` runs the cross-AI panel at every phase close of the remediation. The twelve remaining
rows are mediums; 81 of the 343 commits since 2026-09-23 were panel, review, gate and closure
records.

- (a) **One panel at batch close**, reading each row's exploit test and diff, briefed with the known
  findings. Plus a **pre-run panel** of the two companion documents (this one and the tests).
- (b) A panel per row, as today.
- (c) A panel per three rows.

**Recommendation: (a).** The pre-run panel reviews the definition of done, which is where the
defects have landed; the close panel reviews what shipped. `D-IMPL-352`'s reason ("I don't want to
get to the end to discover we missed a critical item") is preserved because every row has a
sabotage-confirmed test before the panel sees it, and the CRITICAL and HIGHs are already closed
under the per-wave regime.

### Q2 — Are the seven low rows in the run?

- (a) **Five in, two ruled**: fix the non-ASCII bearer, the `key_id` traversal, the cache key, the
  `.gitignore` patterns and the algorithmic lint; rule the reserved entry-point denial and the
  `mcp_stdio` environment pass-through as **disclosed deployment limitations** on the security page.
- (b) All seven fixed.
- (c) None; lows wait.

**Recommendation: (a).** The five are each under an hour of mechanism with a one-line test. The
two are deliberate designs with recorded reasons; fixing them is a design change, not a repair.

### Q3 — Are the example lows EX-07…EX-10 in the run?

- (a) **EX-09 and EX-10 in** (quote `search_path` with `sql.Identifier` in seven modules; curate the
  LangGraph client's child environment), EX-07 and EX-08 as README notes only.
- (b) All four in.
- (c) None; examples are frozen specimens (`D-IMPL-261`).

**Recommendation: (a).** EX-09 is an objectively wrong example (unquoted identifier), which
`D-IMPL-261` allows fixing. EX-07 and EX-08 are hazards only when the example is wrapped as a
service, which the READMEs can say in a sentence.

### Q4 — No tag in this run

SEC-029 closes when `v1.0.2` is tagged, by the stamp check already wired. Tagging is a release act
under the "nothing has shipped" ruling and the SEC-029 release hold.

- (a) **No tag in this run.** The run ends with the rows merged and the ledger updated; tagging is a
  separate GO.
- (b) Tag at batch close if the panel is clean.

**Recommendation: (a).**

### Q5 — SEC-009 erasure: park it, or rule U1–U12 now?

The design on `proposal-d-impl-367-erasure-design` @ `0311766d` names twelve unresolved choices.
None reopens a locked axis. Ruling them does not start implementation; `D-IMPL-367` still requires
its own GO for the panel, the tests and the build.

- (a) **Park SEC-009 out of the run**; rule U1–U12 in a separate sitting.
- (b) Rule U1–U12 now (table below) and let the run include the erasure **tests and panel**, not
  the build.
- (c) Rule U1–U12 now and include the build.

**Recommendation: (a).** Erasure touches the artifact store, the graph and replay. It is the one
remaining row where a wrong choice is expensive to unwind, and it has no exploit test in the sense
the other rows do. It deserves its own attention, not a slot in a mechanical batch.

If Dave prefers (b) or (c), the twelve, with the design's own recommendations:

| # | Choice | Design's recommendation |
| --- | --- | --- |
| U1 | may an erasure subject be a principal identifier? | no, this phase; route through U3 |
| U2 | the replay-input path list as an SDK mechanism constant the declaration validator refuses against | yes; it lists the SDK's own field names, not domain values |
| U3 | pseudonymization at write for audit actors | not designed here; its own entry |
| U4 | `subject_ref` representation on the record | hashed with a deployment-declared salt per subject class |
| U5 | whole-artifact vs field-scoped erasure first | whole-artifact first; field-scoped is G10 phase 3 |
| U6 | an un-erasure record | no |
| U7 | index substrate: boot-time scan vs append-only registry mirror | the registry mirror, with the record as the only authority |
| U8 | does `exists` consult the erasure index? | no |
| U9 | the request/approval as a deployment-declared workflow vs an SDK-shipped shape | deployment-declared, factory-validated |
| U10 | a minimum age before erasure | present on the contract, no SDK default |
| U11 | HTTP status for `erased-content` | 410 at `reasoned`/`full`; the route's not-found rendering at `minimal` |
| U12 | the decorating store composed always vs only when declared | always |

### Q6 — The cap per row

- (a) **Two rounds**: the fix, then at most one re-fix after a sabotage or test failure. Not done
  after round two means the row stops and is written up as unfinished.
- (b) Three rounds.
- (c) A wall-clock or spend figure Dave names instead of rounds.

**Recommendation: (a).** Rounds are observable in the commit log; a spend figure is not, and I
have no instrument to measure it from inside the run. If Dave wants a spend figure as well, it
becomes a second stop condition, whichever fires first.

### Q18 — Who executes and who reviews

- (a) **Opus executes; Fable, Cursor and Codex review** (the former OpenAI engineer's suggestion,
  and Dave's wording). Fable reviews and does not execute, which keeps the panel independent of
  the executor per `D-GATE-21`.
- (b) Opus executes; Codex, Cursor and Gemini review (the `D-IMPL-356` trio).
- (c) Fable executes; Opus, Cursor and Codex review.

**Recommendation: (a), with one condition carried from the record:** Codex on this host has exited
0 having read nothing; every reviewer's output is checked for symbols that resolve against the
tree before it counts, and a reviewer that fails that check is recorded as failed, not as a
reviewer (CLAUDE.md §3.1).

### Q19 — The owed docs fix on `main`

`docs/D-IMPL-366-CLOSE-REVIEWS.md` row A8 cites `runtime/ccf_runtime/cli/local.py` by line number (line 136),
which raised the line-citation ratchet from 365 to 366; the `D-IMPL-366` closure amendment's
sentence "population unchanged at 365" was false when written. Docs only.

- (a) **GO**: re-cite A8 by `::Symbol`, append a dated correction to the closure amendment.
- (b) Carry it.

**Recommendation: (a).** It is a false sentence on `main` and the fix is ten minutes.

### Q20 — Merge authority inside the run

- (a) **Rows merge to a batch integration branch without a GO** when their four conditions hold;
  **one GO from Dave at batch close** merges the integration branch to `main` after the panel.
- (b) Each row's merge to `main` needs Dave's GO.
- (c) Rows merge to `main` without a GO; Dave reviews at batch close.

**Recommendation: (a).** It is the only option that is both unattended between rows and keeps
`main` as the approved-state branch (CLAUDE.md §2.2). If three rows come in clean, this is also
the shape a later continuous run would use.

## 2. Row design rulings

### Q7 — SEC-013: how a second process is refused a writer

- (a) **A lease method on the graph storage Protocol**, with reference implementations: a Postgres
  advisory lock keyed on the graph identity; an exclusive lock file beside the SQLite database; the
  in-memory store declares itself single-process by name and keeps the module set. `_writer.py`
  acquires the lease before minting and releases it with the boot token.
- (b) Keep the process-local set; disclose "one process per graph" as a deployment limitation.
- (c) An external coordination service (etcd, Redis) behind a Protocol.

**Recommendation: (a).** Single-writer is "architectural, not advisory" (CLAUDE.md §10); a
disclosure is not an enforcement. (c) adds a dependency the SDK has avoided everywhere else.

### Q8 — SEC-014: fixed modes or a knob

- (a) **Fixed `0o600` files and `0o700` directories, no configuration.**
- (b) A constructor parameter with those as defaults.

**Recommendation: (a).** A knob that can only loosen is a knob a bank's reviewer has to prove is
unused.

### Q9 — SEC-015: who bumps the pinned SHAs

- (a) **`.github/dependabot.yml` for `github-actions`**, weekly, so pins move by pull request.
- (b) Pin and bump by hand.

**Recommendation: (a).**

### Q10 — SEC-017: close the `D-IMPL-129` gap

`D-IMPL-129` ruled the three tools could not be entitled "without governance machinery the SDK does
not have." The grant now carries `tenants` (added for SEC-018), which is exactly that machinery for
the tenancy question.

- (a) **Entitle all three by the grant's `tenants`**, delete the pinned fail-when-fixed test by
  name, record `D-IMPL-129` superseded.
- (b) Leave as ruled.

**Recommendation: (a).** The premise of `D-IMPL-129` no longer holds.

### Q11 — SEC-019: close on the evidence

The rider shipped in wave 2 (`required-absent` in `src/ccf/products/constraints.py::ConstraintRefusal`, four tests) and was
"retained" rather than closed at `D-GATE-358`.

- (a) **Record SEC-019 CLOSED** after the sabotage check reddens the three cases.
- (b) Keep it open pending something else Dave names.

**Recommendation: (a).** This moves the ledger to 14 of 29 with no new code.

### Q12 — SEC-020: how a withheld subject becomes indistinguishable

- (a) **Constant-fill**: a Π-withheld subject renders exactly as a nonexistent one; debt, emptiness
  and the TTL anchor are not computed for it. Non-withheld subjects are untouched.
- (b) Compute debt and emptiness after projection for every subject.

**Recommendation: (a).** (b) changes the debt semantics and the served addresses of every product,
which the row's regression guard forbids. (a) changes only the withheld path.

### Q13 — SEC-021: the pending-buffer cap

- (a) **A required `max_pending` constructor parameter, no SDK default**, matching
  `max_message_bytes` which is already required with no default. Overflow is a typed refusal.
- (b) An SDK default (for example 1,024).

**Recommendation: (a).** A buffer size is a deployment's capacity decision; the SDK has refused to
guess such values everywhere else (no default temporal window, `D-IMPL-356`).

### Q14 — SEC-022: the replay defense's three parts

1. **Window source**: (a) **the fabric clock injected in wave 2**; (b) a wall clock.
2. **Seen-set substrate**: (a) **in-process by default, behind a small Protocol** so a deployment
   with several receivers can plug a shared one; (b) in-process only; (c) required shared store.
3. **Window length**: (a) **declared in the A2A trust-policy artifact, no SDK default**; (b) a
   default.
4. **Envelopes without the new claims**: (a) **refused**; (b) admitted with a warning for one release.

**Recommendation: (a) on all four.** Each follows a ruling already made: the clock (`D-IMPL-358`),
no SDK defaults (`D-IMPL-356`), correctness over compatibility (`D-IMPL-293`).

### Q15 — SEC-023: who may assert a classification

- (a) **The policy bundle declares, per source, whether it is authoritative for the classification
  attribute.** An assertion from a non-authoritative source is **refused and audited**; an
  authoritative source may set it in either direction.
- (b) As (a), but an authoritative source may not lower a classification (downgrade refused).
- (c) First writer wins; later assertions refused regardless of source.

**Recommendation: (a).** (b) makes a correction impossible without an out-of-band action, and the
authority already carries the responsibility. (c) lets an unauthorized source win by speaking first.

### Q16 — SEC-025: the subject echo on child legs

- (a) **Every child leg returns the subject it answered; the composite refuses by name on any
  mismatch**, on every leg kind (local, `mcp`, A2A), and the refusal names the leg, not the subject.
- (b) Verify on remote legs only; trust local dispatch.

**Recommendation: (a).** The review's reproduction was on local dispatch.

### Q17 — SEC-028: the lock tool

- (a) **pip-tools**: `requirements.lock` from `pip-compile --generate-hashes`; CI installs with
  `pip install --require-hashes -r requirements.lock` then `-e . --no-deps`.
- (b) **uv**: `uv.lock`, `uv sync --frozen` in CI.
- (c) Poetry.

**Recommendation: (a).** It keeps pip, which every Makefile target and both READMEs already use, and
produces a file a bank's dependency scanner reads without a new tool. (b) is faster but adds a
tool to the install story at the moment the install story is being audited.

## 3. What happens after the rulings

1. The `D-IMPL-368` entry records every ruling with its date and this document's commit.
2. The pre-run panel (Q1) reads both companion documents; blocking findings are fixed in the
   documents before any code.
3. The run starts with the three rows that need no design ruling (SEC-014, SEC-024, SEC-026) so the
   model is exercised on the cheapest rows first. If all three come in inside the cap and the
   sabotage reddens each, the run continues to the rest. If not, it stops there, having spent
   three rows' worth.
4. No continuous run is authorized by this document. That is a separate GO after step 3's first
   three rows are measured.
