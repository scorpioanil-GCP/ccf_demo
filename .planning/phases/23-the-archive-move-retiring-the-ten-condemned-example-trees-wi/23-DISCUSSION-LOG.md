# Phase 23: The Archive Move — Retiring the Ten Condemned Example Trees Without Deleting Them - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-24
**Phase:** 23-the-archive-move-retiring-the-ten-condemned-example-trees-wi
**Areas discussed:** phase scope (which trees travel), the paired tests and the suite baseline, archive location, archive runnability, the sweep's ownership table, what `Partial`'s done-limb may claim

**How this sitting went, recorded because it matters:** the gray-area menu was
**rejected** rather than answered. Dave asked a question about the phase's
premise instead — *"Isn't the S1 pair what we just completed, client side
examples?"* — and the check falsified the drafted entry, not the question. The
scope correction, both `D-IMPL-190` rulings and one of the two findings against
`CLNT-17` all descend from that one question. The entry was corrected mid-sitting,
before planning and before any criteria were written.

---

## Phase scope — which trees travel?

| Option | Description | Selected |
|--------|-------------|----------|
| All twelve condemned trees | `DOCS-17`'s ten plus `CLNT-17`'s `s1` pair, as `D-IMPL-189` covers both rows | |
| Ten trees; `s1` pair excluded | `DOCS-17` only; `CLNT-17` untouched at `Not built` | ✓ |

**User's choice:** ten trees — *"let's correct the entry"*.
**Notes:** Dave's challenge exposed that the drafted entry was wrong on its own
premise. The client-side pair is `hw1-companies-over-revenue` (Aug 16) and
`hw1-harness-clients` (Aug 20); `s1-00` (Aug 14) is the PREDECESSOR that
`hw1-companies-over-revenue` rebuilt, same scenario, and `s1-01` (Aug 10) is not
a client example at all. Dave then tested the reasoning — *"you are recommending
we keep the s1 examples because they do not buy us much for the amount of work…
is that correct?"* — and the answer was **no**: the benefit is **zero**, not
small, because neither `s1` tree is in the `examples:` aggregate; and the real
cost is that archiving `s1-01` would make a `D-IMPL-189` commitment false. The
third and strongest measurement surfaced only under that challenge: both `s1`
trees are live fixtures for `tests/deployment`, `tests/products`, `tests/replay`
and `tests/halflife`. Logged as `D-IMPL-190` ruling 1.

---

## The paired tests and the suite baseline

| Option | Description | Selected |
|--------|-------------|----------|
| A — paired tests move with the trees | `D-IMPL-189` point 1 as written; 515 tests leave the suite; baseline 4105 → ~3590 | |
| B — sources move, tests stay under `tests/` and are re-pointed | Baseline holds byte-for-byte at 4105 / 118 | ✓ |

**User's choice:** B.
**Notes:** The ambiguity was flagged rather than guessed — *"leaving the test
files intact"* admitted both a narrow reading (the `s1` trees stay) and a wide
one (B), and they are different phases. Dave confirmed B. This AMENDS
`D-IMPL-189` point 1; the old and new clauses are both named in `D-IMPL-190`
per the standing policy `D-GATE-22` set for `D-IMPL-188`. The deciding
measurement — `pyproject.toml:142` `testpaths = ["tests"]`, `tests/examples`
collecting 515 tests, and a 4105 / 118 baseline four gates cite as proof of no
behaviour change — was not available when `D-IMPL-189` was written.

---

## Archive location

| Option | Description | Selected |
|--------|-------------|----------|
| Inside `examples/` (e.g. `examples/_archive/`) | Keeps the trees under the same root; `examples/` becomes mostly archive | |
| Outside `examples/` (e.g. `archive/examples/`) | `examples/` keeps meaning "things we teach with" | ✓ |

**User's choice:** outside — accepted as recommended.
**Notes:** Mechanically neutral either way; `pymdownx.snippets` resolves
`base_path` against the repo root, not `public/`. Logged as `D-IMPL-191` ruling 1.

---

## Archive runnability and the `make` targets

| Option | Description | Selected |
|--------|-------------|----------|
| Runnable, targets renamed to an archive form | Keeps `make` access to the archived examples | |
| Runnable, all ten targets deleted | Archive stays importable/executable; no target invites running it | ✓ |
| Not runnable — cold storage | Rejected: two condemned-tree tests execute rather than read | |

**User's choice:** runnable, no targets — accepted as recommended.
**Notes:** `tests/examples/test_cross_process_output.py` and
`test_ext00_hardening.py` invoke `subprocess`/`runpy`, so executability is
forced regardless of preference. 6 of 31 `tests/examples` files execute; the
other four are `hw1`, not condemned. Logged as `D-IMPL-191` ruling 2.

---

## The sweep's `Retirement` table

| Option | Description | Selected |
|--------|-------------|----------|
| Re-point owners to Phase 23; archived paths still count as couplings | Deletion is still owed, so the coupling is still real | ✓ |
| Make the sweep skip archived paths | Rejected: reproduces the Phase 22.1 defect — a tool reporting clean because it did not look | |

**User's choice:** re-point and keep counting — accepted as recommended.
**Notes:** `tools/retirement_sweep.py:131-167` attributes all twelve trees to
`16-15`/`16-17`/`16-18` (retired at `D-IMPL-152`) and `17-08` (blocked at task
3), so no live plan owns those rows today. The `s1` pair's `17-08` rows are left
untouched. Logged as `D-IMPL-191` ruling 3.

---

## What `Partial`'s done-limb may claim

| Option | Description | Selected |
|--------|-------------|----------|
| `D-IMPL-189` point 3 verbatim — "out of live CI" | Would be FALSE the day it is written | |
| "Out of the `examples:` aggregate", naming what still exercises them | Accurate under ruling B | ✓ |

**User's choice:** the narrowed wording — accepted as recommended.
**Notes:** This is a push-back on `D-IMPL-189`'s own phrasing, not a drafting
preference. Under `D-IMPL-190` ruling 2 the tests stay, so 25 of 31
`tests/examples` files still read the archived sources and 2 still execute them
— the trees leave the aggregate, not CI. Writing *"out of live CI"* would be the
`RECON-09` failure: the difference between a verdict and a hope. Logged as
`D-IMPL-191` ruling 4, naming the old and new clause.

---

## Claude's Discretion

- The archive directory's exact name and internal layout, provided it is outside `examples/` and every include resolves.
- How the include re-point is mechanized (bulk path substitution vs. per-page edit), provided criterion 5's RED-before-GREEN control holds.
- Plan and wave decomposition.

## Deferred Ideas

- **`CLNT-17`'s stated blocker is wrong on the tree** — three `refuse_request` `.py` call sites, two of them in `s1-00`, against a cell claiming `s1-01` is the last. Raised, expressly NOT ruled.
- **`CLNT-17` may be mis-framed as an example-retirement row at all**, given both `s1` trees are core-suite fixtures. Dave's ruling.
- **The `00`–`08` half of `D-27`** (deletion) remains undecided.
- **`DOCS-14` / `EXAM-02`** still owe the replacement surface.
- **The 27-item human-verification packet** — ten of nineteen decision items live, awaiting Dave (`D-20`).
- **Phase 14's `G-01`** — the archived pages teach the pre-Phase-15 integration surface; the move relabels, it does not close.
