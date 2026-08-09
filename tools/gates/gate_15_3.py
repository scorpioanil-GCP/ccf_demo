"""`make gate-15.3` — the Phase 15.3 permitted-change-surface gate (D-IMPL-92).

WHAT THIS ASSERTS
=================

Phase 15.3's claim is normally unfalsifiable — *"the SDK needs no refactor to
accept a new substrate"* is an architectural assertion, and an assertion is not
evidence. D-IMPL-92 reduces it to a statement about a diff:

    Adding a real substrate touched one new module, one writer class, and a
    bounded one-line extension of four existing enumerations — no mechanism
    anywhere in the SDK changed.

That sentence is mechanically checkable, and this script is the check. **The
value of the claim is that it is falsifiable, not that it is universal.** This
gate proves a fact about ONE diff; it is not a general property of the
architecture and must never be read as one.

WHERE THIS LIVES, AND WHY
=========================

`tools/gates/`, not `tools/lints/`. Phase 15.3 CONTEXT.md D-10 is explicit: the
check "lives with the phase rather than in `tools/lints`, because it asserts a
fact about one phase's diff, not a standing invariant." A `tools/lints` rule is
expected to hold forever and to accumulate; this gate is expected to be
**superseded** by substrate #7's gate, not extended into a permanent rule.
What is copied from `tools/lints` is its *output contract* only — findings as
``path:line rule message`` on stdout (`tools/lints/__init__.py:38-40`), a
summary on stderr and `return 1` on any finding (`tools/lints/__main__.py`
`main()` at :240-261), and one named ``RULE_*`` constant per rule
(`tools/lints/harness_imports.py:58-60`). There is no report-only mode (D-07):
the exit code is the only gate signal, because a non-blocking mode is how an
invariant quietly stops being one.

THE TWO LAYERS — WHICH IS THE CLAIM AND WHICH IS ITS APPROXIMATION
==================================================================

D-IMPL-92 states the ruling in two layers on purpose, and this module keeps
them visibly distinct because a reader must be able to tell them apart.

**LAYER 1 — NORMATIVE. This is the claim.** Not directly enforced here; region
scoping is the right rule and is not greppable. Quoted so the proxy below can
be read against it:

    D-11's hard line is relaxed for the minimum registration surface the
    existing boot and deployment mechanism requires. Permitted for any new
    backend, **each scoped to the named block and nothing else**:

    * `src/ccf/boot.py` — only the explicit backend-selection / exclusivity
      block;
    * `src/ccf/deployment/manifest.py` — only the backend -> required-
      connection-argument mapping;
    * `src/ccf/controlplane/artifacts.py` — only the `backend` `Literal`
      member;
    * `tests/conftest.py` — only the fixtures needed to exercise the new
      backend;
    * `pyproject.toml` and the generated
      `docs/schemas/ccf.deployment-manifest.json` — only the entries required
      to declare, mark and install the backend.

    All other paths under `src/ccf` remain restricted; any further expansion
    requires a new `D-IMPL`. Documentation, backend-specific unit tests, CI
    workflows and the `Makefile` were never inside D-11's `src/ccf`-scoped hard
    line and are free.

**LAYER 2 — MECHANICAL. This is the approximation, and it is what runs.** Four
checks, deliberately conservative, plus the free assertions D-11 and R6 add:

    (1) a **path allowlist** — any changed path outside it fails;
    (2) **no existing backend name is removed** from any enumeration;
    (3) **per-file added-line budgets** taken from the mongo precedent;
    (4) an **AST assertion** that no existing class or function body in
        `src/ccf/graph/_writer.py` is modified, only new ones added.

The budgets are an **admitted proxy** for "extension, not modification" and are
to be tightened to a direct AST check (enumeration members added, nothing else
touched) if any future phase finds them gameable. They are not the claim; they
approximate it. Every budget below is printed beside its TRUE measured mongo
baseline, per the 2026-08-08 correction, so a future reader sees the headroom
rather than inferring it — a budget whose stated derivation is wrong is a
budget nobody will trust when it fires.

THE SECOND CORRECTION (D-IMPL-92, Dave, 2026-08-08) — TWO PROXY EXTENSIONS
=========================================================================

The first run of this gate against the real diff exited 1 on two changes.
Neither was a claim violation: both were **already permitted or forced under
layer 1**, and the failure was that **layer 2 under-enumerated a class layer 1
states in general terms**. The ruling extends the *proxy* and leaves the
*normative rule* exactly as strong — which is the only direction this may ever
move.

1. **Backend-specific unit tests are free as a CLASS, not as one instance.**
   Layer 1 already says so verbatim ("backend-specific unit tests … were never
   inside D-11's `src/ccf`-scoped hard line and are free"), but the Tier-C
   allowlist named only the *new* substrate's module. Adding a required keyword
   argument to `_preflight_backend` forced three identical `fluree_url=None,`
   lines into `tests/graph/test_mongo_backend.py`. The allowlist now names the
   class (`tests/graph/test_*_backend.py`). A bare special case for the mongo
   module was explicitly refused: it would repeat the very under-enumeration
   being fixed.

2. **A conformance suite may carry ONE forced enumeration extension beside its
   param line.** `tests/conformance/test_graphstore.py`'s fixture guards on a
   set literal of backend names; without the new name in that set the added
   `pytest.param` raises `NotImplementedError`, so the param addition is not
   self-contained. That file has **no `#:` block**, so the first correction's
   comment-block permission cannot reach it. The permission granted is
   deliberately tight and mirrors the comment-block one: one added and one
   deleted line whose ONLY difference is that a set/tuple/list literal of
   backend-name strings gained exactly the new backend's name — verified by
   comparing the two lines with every string literal removed — and the change
   is **recorded** (see `check_recorded_in_package`).

THE THIRD CORRECTION (D-IMPL-92, Dave, 2026-08-08) — AND THE RECURSION
=======================================================================

Recording the second correction in `docs/DECISIONS.md` — which CLAUDE.md §11
makes **mandatory** for any `D-IMPL` ruling — put that path in the measured
surface, where Tier C had named `docs/SURFACE-CHANGES.md` and
`docs/surface-changes/*` and omitted the decision log. The gate failed again,
on the record of the fix for the previous failure.

**That recursion is the durable lesson, more than the path is.** The test
layer 1 actually applies is *"was never inside D-11's `src/ccf`-scoped hard
line"*; `docs/DECISIONS.md` is not under `src/ccf` at all, so it is free on the
same footing as the `Makefile` and the CI workflows. Ruling: **Tier C gains
`docs/DECISIONS.md`, bounded APPEND-ONLY** — added lines permitted, any
deletion a finding. The bound is not decoration: it turns the
appended-and-dated correction discipline into a mechanical check, so the entry
stays a check that would still fire if someone rewrote decision history rather
than becoming a hole.

**Broadening Tier C to `docs/**` was considered and rejected.** It would free
`docs/GRAPH_QUERY_SEMANTICS.md`, which the ruling explicitly freezes — real
coverage traded for a tidier allowlist. Named here so a future reader does not
"simplify" it.

The durable lesson, and the reason all of this is in the module docstring
rather than only in the phase record: **the enumeration-is-the-mechanism
finding recurs in the test tree AND in the documentation tree, and this gate's
own allowlist is itself an enumeration that under-enumerated — three times,
the third time recursively, on the record of the second fix.** A reader
comparing layer 1 against layer 2 finds gaps that reading either alone would
miss. That is the argument for recording both.

WHAT THIS GATE DELIBERATELY DOES NOT DO
=======================================

* It does not build a backend **registration seam**. D-IMPL-92 records that as
  a well-evidenced future candidate it *explicitly does not commission*:
  constructing it inside the phase whose whole claim is "no refactor was
  needed" would be precisely the refactor the claim denies.
* It does not permit splitting `src/ccf/graph/_writer.py` into a package. That
  is a carried 15.2 close-review advisory (A5) with no `DI-15.2-NN` entry, and
  a split relocates every existing class — layer-2 check (4) would fail on the
  phase's own refactor.
* It does not re-implement CINV-02. The standing `cinv02-graph-writer` rule in
  `tools/lints/harness_imports.py` already proves no `*GraphWriter` /
  `*GraphTxn` class exists outside `ccf.graph._writer`; this gate asserts
  `python -m tools.lints --all` exits 0 and **cites** that rule.
* It does not regenerate `docs/surface/v0.2-surface.json`. That path carries an
  explicit deny (see `SINGLE_OWNER_DENY`).

MEASUREMENT DISCIPLINE
======================

Everything is measured with ``git diff --numstat BASE...HEAD`` — the FIRST
column is added lines. **The ``--stat`` form of ``git show`` is never used**:
its right-hand column is insertions PLUS deletions, and reading it as "added"
is exactly the error that produced the wrong baselines in BF-1 and in
D-IMPL-92 before its 2026-08-08 correction (52/15/5/40, never 63/20/7/45).

The diff is **three-dot** and therefore commit-to-commit: it does not see the
working tree. A negative test performed as an uncommitted edit makes this gate
exit 0. Negative tests are throwaway commits.

Usage::

    make gate-15.3                       # the only supported invocation
    python -m tools.gates.gate_15_3 --base <sha>
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import pathlib
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from typing import Sequence

from tools.lints import format_finding, read_tree

# --------------------------------------------------------------------------
# Base ref
# --------------------------------------------------------------------------

#: The phase's base ref, **pinned as a literal SHA**.
#:
#: Derivation: this is what ``git merge-base main HEAD`` resolved to at Phase
#: 15.3's start — the commit `main` sat on when the phase opened. It is pinned
#: rather than recomputed for one reason the phase itself demonstrates: this
#: workflow merges each wave's worktree branch into `main` as the wave lands,
#: so by wave 5 ``git merge-base main HEAD`` has advanced to the phase's own
#: tip and a recomputed base would measure an EMPTY diff — a gate that passes
#: everything. The same is true of the post-merge re-verification on `main`,
#: where HEAD *is* `main`. R6 requires the base be recorded "as a literal SHA
#: in the gate package, so the claim is reproducible after `main` moves"; it
#: has moved, so the literal is the only workable base.
#:
#: The gate asserts this SHA is an ancestor of HEAD, prints the live
#: ``git merge-base main HEAD`` beside it so the divergence is visible rather
#: than hidden, and fails if the measured surface does not contain the adapter
#: module (``RULE_BASE_RESOLUTION``) — the guard against a mis-resolved base
#: silently producing a vacuous pass.
PHASE_BASE = "96f54c55bef5469323d7cfc5fad3594f5bdd35a9"

#: The one path whose presence in the measured surface proves the base
#: resolved to something meaningful. A diff that does not contain the new
#: adapter module is not this phase's diff.
ADAPTER_MODULE = "src/ccf/graph/backends/fluree.py"

# --------------------------------------------------------------------------
# Rule names — one named constant per rule (tools/lints/harness_imports.py
# :58-60 convention). The rule token is the second whitespace-separated field
# of every finding.
# --------------------------------------------------------------------------

RULE_SELF_TREE = "gate153-self-tree"
RULE_DIRTY_TREE = "gate153-dirty-tree"
RULE_BASE_RESOLUTION = "gate153-base-resolution"
RULE_SINGLE_OWNER = "gate153-single-owner"
RULE_PATH_ALLOWLIST = "gate153-path-allowlist"
RULE_APPEND_ONLY = "gate153-append-only"
RULE_BACKEND_REMOVED = "gate153-backend-removed"
RULE_BUDGET = "gate153-budget"
RULE_SCHEMA_CONSISTENCY = "gate153-schema-consistency"
RULE_WRITER_AST = "gate153-writer-ast"
RULE_CONFORMANCE = "gate153-conformance"
RULE_CORPUS = "gate153-corpus"
RULE_FROZEN = "gate153-frozen"
RULE_LINT = "gate153-lint"
RULE_PACKAGING = "gate153-packaging"

# --------------------------------------------------------------------------
# Layer-2 check (1): the path allowlist
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Allowed:
    """One allowlist entry: a pattern, its tier, and the reason it is allowed.

    The reason field is not decoration. `tools/lints/__main__.py:100-109` and
    `citations.py:153-164` establish the convention this borrows: *what a check
    does not cover is stated, not left to path accident*. An allowlist whose
    entries carry no reason is a list nobody can audit.
    """

    pattern: str
    tier: str
    reason: str
    #: When true, the path may only GROW: added lines are permitted, any
    #: deletion is a finding. This is how a *documented discipline* becomes a
    #: *mechanical* one. Used for `docs/DECISIONS.md`, whose whole value rests
    #: on corrections being appended and dated rather than edited into the
    #: entry they correct — a bound of zero deletions encodes exactly that and
    #: keeps the allowlist entry a real check rather than a hole.
    append_only: bool = False


#: Patterns are `fnmatch` — note that `*` crosses directory separators there,
#: so `.planning/*` covers the whole tree beneath it. Stated rather than
#: relied on silently.
ALLOWLIST: tuple[Allowed, ...] = (
    # --- Tier A: the adapter surface. Unbounded; new or additive. -----------
    Allowed(
        ADAPTER_MODULE,
        "A",
        "the ONE new module — the substrate adapter itself (D-10, D-IMPL-92)",
    ),
    Allowed(
        "src/ccf/graph/_writer.py",
        "A",
        "the ONE writer module — CINV-02 confines every *GraphWriter/*GraphTxn"
        " class here, so a new substrate's writer has nowhere else to go."
        " Bounded instead by layer-2 check (4): only NEW top-level classes and"
        " functions may appear",
    ),
    # --- Tier B: registration sites. Bounded; enumeration-extension only. ---
    Allowed(
        "src/ccf/boot.py",
        "B",
        "the explicit backend-selection / exclusivity block. There is no"
        " registration seam: this enumeration IS the mechanism (D-IMPL-92"
        " structural finding). Budgeted",
    ),
    Allowed(
        "src/ccf/deployment/manifest.py",
        "B",
        "the backend -> required-connection-argument mapping. Same structural"
        " finding. Budgeted",
    ),
    Allowed(
        "src/ccf/controlplane/artifacts.py",
        "B",
        "the `backend` Literal member. Budgeted",
    ),
    Allowed(
        "pyproject.toml",
        "B",
        "the pytest marker registration. No budget: D-IMPL-92 sets none",
    ),
    Allowed(
        "docs/schemas/ccf.deployment-manifest.json",
        "B",
        "generated from the `backend` Literal. No budget; asserted CONSISTENT"
        " with the Literal instead (RULE_SCHEMA_CONSISTENCY)",
    ),
    Allowed(
        "tests/conftest.py",
        "B",
        "only the fixtures needed to exercise the new backend. Budgeted",
    ),
    Allowed(
        "tests/conformance/test_substrate_differential.py",
        "B",
        "one added pytest.param line plus the `#:` comment block immediately"
        " above the param tuple (D-IMPL-92 correction, 2026-08-08)",
    ),
    Allowed(
        "tests/conformance/test_graphstore.py",
        "B",
        "one added pytest.param line plus the `#:` comment block immediately"
        " above the param tuple (D-IMPL-92 correction, 2026-08-08)",
    ),
    # --- Tier R: recorded, not blocked. -------------------------------------
    Allowed(
        "tests/conformance/query_corpus.py",
        "R",
        "D-11: a corpus addition is PERMITTED but must be justified in the"
        " gate package. Blocked here would create exactly the pressure D-11"
        " names — an executor talked out of adding a fixture that ought to be"
        " added. See RULE_CORPUS",
    ),
    # --- Tier C: free. Evidence and operations, never SDK mechanism. --------
    Allowed(
        "tests/graph/test_*_backend.py",
        "C",
        "backend-specific unit tests, as a CLASS. D-IMPL-92 layer 1 already"
        " frees them verbatim; the first cut of this allowlist named only the"
        " new substrate's module and so failed on the three `fluree_url=None,`"
        " lines that a new required keyword argument on `_preflight_backend`"
        " forced into test_mongo_backend.py. Extended to the class by the"
        " 2026-08-08 second correction. Naming the one offending FILE was"
        " refused: a special case would repeat the under-enumeration being"
        " fixed. (fnmatch `*` crosses separators, so a nested"
        " tests/graph/**/test_*_backend.py would match too — stated, not"
        " relied on.)",
    ),
    Allowed(
        ".github/workflows/*",
        "C",
        "CI workflows were never inside D-11's src/ccf-scoped hard line"
        " (D-IMPL-92 layer 1)",
    ),
    Allowed(
        "Makefile",
        "C",
        "the developer/CI command surface; never inside the hard line"
        " (D-IMPL-92 layer 1)",
    ),
    Allowed(
        "tools/gates/*",
        "C",
        "this gate itself. A gate that could not add itself could not exist",
    ),
    Allowed(
        "docs/SURFACE-CHANGES.md",
        "C",
        "the assembled D-15B migration note; documentation is free"
        " (D-IMPL-92 layer 1)",
    ),
    Allowed(
        "docs/DECISIONS.md",
        "C",
        "the decision log — free on the same footing as the Makefile and the"
        " CI workflows, because the test layer 1 actually applies is 'was"
        " never inside D-11's src/ccf-scoped hard line' and this path is not"
        " under src/ccf at all. Added by the 2026-08-08 THIRD correction, and"
        " mandatory rather than incidental: CLAUDE.md §11 requires every"
        " D-IMPL ruling to be logged here, so a gate that fails because the"
        " project's own decision-logging rule was followed is measuring the"
        " wrong thing. APPEND-ONLY: corrections are appended and dated, never"
        " edited into the entry they correct (the D-IMPL-86/-87/-92"
        " discipline), so a deletion here is rewritten history and stays a"
        " finding. Broadening this to `docs/**` was considered and REJECTED —"
        " it would free docs/GRAPH_QUERY_SEMANTICS.md, which the ruling"
        " explicitly freezes, trading real coverage for a tidier allowlist.",
        append_only=True,
    ),
    Allowed(
        "docs/surface-changes/*",
        "C",
        "the per-plan surface fragment. NOTE: a DIFFERENT directory from"
        " docs/surface/ — see SINGLE_OWNER_DENY",
    ),
    Allowed(
        ".planning/*",
        "C",
        "the phase record: plans, summaries, STATE.md, ROADMAP.md. Not code",
    ),
)

#: Evaluated BEFORE the allowlist, and it emits a finding then lets execution
#: continue — it is a narrower pre-filter on the same path set, not an early
#: return. Short-circuiting here would suppress checks 2-4 in the same run,
#: which is the only way this ordering could do harm.
#:
#: `docs/surface/v0.2-surface.json` would fail as an unlisted path anyway, but
#: the finding would read "path not in allowlist", which teaches a future
#: executor nothing. A deny whose message states the rule is the difference
#: between a gate that teaches and a gate that merely blocks.
SINGLE_OWNER_DENY: dict[str, str] = {
    "docs/surface/v0.2-surface.json": (
        "SINGLE-OWNER ARTIFACT. Makefile:244-251 reserves regeneration of the"
        " live public-surface manifest for exactly two plans — 15-01 at phase"
        " start and 15-21 at phase close. Every in-flight plan runs"
        " `tools/dump_surface.py --report` and writes a fragment at"
        " docs/surface-changes/<plan>-<slug>.md instead. That is a DIFFERENT"
        " directory from docs/surface/, and the near-miss is exactly how a"
        " plan talks itself into regenerating the manifest. Remedy: revert"
        " this path and write docs/surface-changes/<plan>-<slug>.md"
    ),
}

# --------------------------------------------------------------------------
# Layer-2 check (2): no existing backend name removed
# --------------------------------------------------------------------------

#: The three files whose enumerations ARE the registration mechanism. Note
#: that this check is deliberately NOT "additive-only, zero deletions": the
#: mongo landing deleted 11 lines in `boot.py`, all docstring sentences
#: rewritten to enumerate one more backend. The change *kind* is "one more
#: member of an existing enumeration", not "a modification of a mechanism",
#: and a zero-deletions rule would fail on it (PATTERNS §7).
ENUMERATION_FILES: tuple[str, ...] = (
    "src/ccf/boot.py",
    "src/ccf/deployment/manifest.py",
    "src/ccf/controlplane/artifacts.py",
)

#: Where the pre-existing backend names are DERIVED from (never hard-coded):
#: the `backend` Literal in the base ref's `artifacts.py`.
LITERAL_SOURCE = "src/ccf/controlplane/artifacts.py"

# --------------------------------------------------------------------------
# Layer-2 check (3): per-file added-line budgets
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Budget:
    """An added-line budget and the TRUE measured mongo baseline behind it."""

    limit: int
    mongo_baseline: int
    note: str


#: Budgets per D-IMPL-92 as corrected 2026-08-08. The baselines are the real
#: `git diff --numstat` FIRST-column counts across `dfb2f80`/`e854946`/
#: `761fba1` — 52/15/5/40 — NOT the 63/20/7/45 that BF-1 read off the
#: insertions-plus-deletions column of `git show`'s `--stat` form.
BUDGETS: dict[str, Budget] = {
    "src/ccf/boot.py": Budget(70, 52, "unchanged by the correction"),
    "src/ccf/deployment/manifest.py": Budget(25, 15, "unchanged by the correction"),
    "src/ccf/controlplane/artifacts.py": Budget(10, 5, "unchanged by the correction"),
    "tests/conftest.py": Budget(
        50,
        40,
        "RAISED from 45 by the 2026-08-08 correction: five lines of headroom on"
        " a structurally identical addition measures noise rather than"
        " refactoring, and a gate that fires spuriously trains an executor to"
        " game the number instead of respecting the rule",
    ),
}

# --------------------------------------------------------------------------
# Layer-2 check (4): the _writer.py AST assertion
# --------------------------------------------------------------------------

WRITER_MODULE_PATH = "src/ccf/graph/_writer.py"

#: The additions this phase expects. Named so an UNEXPECTED addition is
#: legible in the finding rather than merely counted.
WRITER_EXPECTED_ADDITIONS: frozenset[str] = frozenset(
    {"_fluree_claim_projection", "_FlureeTxn", "FlureeGraphWriter"}
)

# --------------------------------------------------------------------------
# The conformance-suite rule, exactly as corrected
# --------------------------------------------------------------------------

#: The one added line each suite is permitted, verbatim.
CONFORMANCE_PARAM_RE = re.compile(
    r'pytest\.param\("fluree",\s*marks=pytest\.mark\.fluree\)'
)

#: Per suite: the regex anchoring the param container, so the `#:` comment
#: block "immediately above the param tuple" is located structurally rather
#: than by trusting any `#:` line anywhere in the file.
CONFORMANCE_SUITES: dict[str, str] = {
    "tests/conformance/test_substrate_differential.py": r"^BACKEND_PARAMS\s*=\s*\(",
    "tests/conformance/test_graphstore.py": r"^\s*params\s*=\s*\[",
}

# --------------------------------------------------------------------------
# The corpus rule — recorded, not blocked
# --------------------------------------------------------------------------

CORPUS_PATH = "tests/conformance/query_corpus.py"

GATE_PACKAGE = (
    ".planning/phases/15.3-fluree-adapter-tier-1-substrate-inserted/"
    "15.3-GATE-PACKAGE.md"
)

#: The three parts D-11 requires of a corpus justification: (a) what shape was
#: added, (b) why it was needed, (c) the D-11 classification.
CORPUS_SHAPE_RE = re.compile(r"\bshape\b", re.IGNORECASE)
CORPUS_WHY_RE = re.compile(r"\bwhy\b", re.IGNORECASE)
CORPUS_CLASSIFICATION_RE = re.compile(
    r"exposes a gap in the 15\.2 corpus|a Fluree quirk", re.IGNORECASE
)
CORPUS_SECTION_RE = re.compile(r"^#{1,6}\s+.*corpus", re.IGNORECASE)

# --------------------------------------------------------------------------
# Free assertions
# --------------------------------------------------------------------------

#: Byte-frozen across the whole phase. D-11 makes the GRAPH_QUERY_SEMANTICS
#: freeze a hard line (amendments go in the `GQ-35` lane, line-number-neutral);
#: the 15.2 gate asserted both perf paths byte-untouched. One line of script
#: each, replacing a sentence of prose.
FROZEN_PATHS: tuple[str, ...] = (
    "docs/GRAPH_QUERY_SEMANTICS.md",
    "perf/baselines/",
    "perf/thresholds.toml",
)

#: The standing invariant this gate CITES rather than re-implements. The
#: `cinv02-graph-writer` rule inside `tools/lints/harness_imports.py` already
#: proves no `*GraphWriter`/`*GraphTxn` class exists outside `ccf.graph._writer`;
#: re-implementing that AST walk here would put a standing invariant in a
#: phase-local gate, which is the location mistake D-10 forbids.
CITED_LINT_RULE = "cinv02-graph-writer"

# --------------------------------------------------------------------------
# Packaging-absence assertions (SUBQ-14 evidence — cheap, and each recorded)
# --------------------------------------------------------------------------

CI_WORKFLOW = ".github/workflows/ci.yml"
CI_INSTALL_RE = re.compile(r"pip install -e")
PLC0415 = "PLC0415"
BOOT_PATH = "src/ccf/boot.py"
FLUREE_MARKER_RE = re.compile(r"^\s*\"fluree:")
OPTIONAL_EXTRA_CLAUSE_RE = re.compile(r"requires the optional", re.IGNORECASE)


# --------------------------------------------------------------------------
# git plumbing
# --------------------------------------------------------------------------


def git(root: pathlib.Path, *args: str) -> str:
    """Run a READ-ONLY git command in `root` and return stdout."""
    proc = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 and not proc.stdout:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def git_ok(root: pathlib.Path, *args: str) -> bool:
    """True when a read-only git command exits 0 (used for --exit-code forms)."""
    proc = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=False
    )
    return proc.returncode == 0


def blob(root: pathlib.Path, ref: str, path: str) -> str | None:
    """The content of `path` at `ref`, or None when it did not exist there."""
    proc = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout if proc.returncode == 0 else None


@dataclass(frozen=True)
class Change:
    """One changed path with its `--numstat` counts (FIRST column is added)."""

    path: str
    added: int
    deleted: int
    status: str


def measure(root: pathlib.Path, base: str) -> list[Change]:
    """The three-dot change surface `base`...HEAD, with per-path counts.

    Three dots: changes on THIS side only. `--numstat` always; the `--stat`
    form of `git show` never (its right column is added PLUS deleted).
    """
    status: dict[str, str] = {}
    for line in git(root, "diff", "--name-status", f"{base}...HEAD").splitlines():
        if not line.strip():
            continue
        fields = line.split("\t")
        status[fields[-1]] = fields[0]

    changes: list[Change] = []
    for line in git(root, "diff", "--numstat", f"{base}...HEAD").splitlines():
        if not line.strip():
            continue
        added_s, deleted_s, path = line.split("\t", 2)
        added = 0 if added_s == "-" else int(added_s)
        deleted = 0 if deleted_s == "-" else int(deleted_s)
        changes.append(Change(path, added, deleted, status.get(path, "?")))
    return sorted(changes, key=lambda c: c.path)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def allowed_for(path: str) -> Allowed | None:
    """The allowlist entry covering `path`, or None."""
    for entry in ALLOWLIST:
        if fnmatch.fnmatchcase(path, entry.pattern):
            return entry
    return None


def literal_backend_names(source: str) -> frozenset[str]:
    """The `backend` Literal members in an `artifacts.py` source.

    Derived from the AST, never hard-coded: the enumeration is the mechanism,
    so the names must come from the mechanism.
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue
        value = node.value
        name = (
            value.id
            if isinstance(value, ast.Name)
            else value.attr if isinstance(value, ast.Attribute) else None
        )
        if name != "Literal":
            continue
        slc = node.slice
        elts = slc.elts if isinstance(slc, ast.Tuple) else [slc]
        members = {
            e.value for e in elts if isinstance(e, ast.Constant) and isinstance(e.value, str)
        }
        if "sqlite" in members:
            return frozenset(members)
    return frozenset()


def top_level_defs(source: str, path: pathlib.Path) -> dict[str, ast.AST]:
    """Top-level ClassDef/FunctionDef nodes by name, parsed via tools.lints."""
    module = read_tree(source, path)
    return {
        node.name: node
        for node in module.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }


def module_level_statements(source: str, path: pathlib.Path) -> list[ast.stmt]:
    """Every top-level statement that is NOT a class or function definition.

    The complement of `top_level_defs` over the same module body: imports,
    `__all__`, module constants, SQL/query string constants, and anything else
    that executes at import time. Added by the 2026-08-08 FOURTH correction —
    before it, `_writer.py` was a Tier-A path with no line budget whose
    module-level constants no check looked at, so rewriting one passed
    everything (review finding WR-09).
    """
    module = read_tree(source, path)
    return [
        node
        for node in module.body
        if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def name_collection(node: ast.stmt) -> tuple[str, list[str]] | None:
    """`(target, members)` when `node` binds a flat literal collection of strings.

    Matches `NAME = [...]`, `NAME = (...)`, `NAME = {...}` and their annotated
    forms, and ONLY when every element is a plain string constant. Anything
    else — a comprehension, a concatenation, a non-string element, a tuple or
    attribute target — returns None and is therefore not eligible for the
    bounded companion permission below.
    """
    if isinstance(node, ast.Assign):
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            return None
        target = node.targets[0].id
        value: ast.expr | None = node.value
    elif isinstance(node, ast.AnnAssign):
        if not isinstance(node.target, ast.Name) or node.value is None:
            return None
        target = node.target.id
        value = node.value
    else:
        return None
    if not isinstance(value, (ast.List, ast.Tuple, ast.Set)):
        return None
    members: list[str] = []
    for element in value.elts:
        if not isinstance(element, ast.Constant) or not isinstance(element.value, str):
            return None
        members.append(element.value)
    return target, members


def bounded_name_addition(
    before: ast.stmt, after: ast.stmt, permitted: frozenset[str]
) -> str | None:
    """The ONE name `after` adds to `before`'s string collection, or None.

    The `_writer.py` companion permission granted by D-IMPL-92's 2026-08-08
    FOURTH correction, bounded as tightly as the two conformance companions it
    mirrors. ALL of:

    * the two statements are the same statement kind and bind the same name;
    * both values are flat literal collections of string constants;
    * the after-members are the before-members plus **exactly one**; and
    * that one is in `permitted` — which the caller derives from the mechanism
      (a NEW top-level definition in this same module whose name begins with a
      backend name this phase ADDED to the `backend` `Literal`), never from a
      hard-coded list.

    Everything else at module level in `_writer.py` — including any other edit
    to `__all__` — remains a finding. This is a permission for one name, not a
    blanket exemption for module-level assignments.
    """
    if type(before) is not type(after):
        return None
    pair_before = name_collection(before)
    pair_after = name_collection(after)
    if pair_before is None or pair_after is None:
        return None
    if pair_before[0] != pair_after[0]:
        return None
    if len(pair_after[1]) != len(pair_before[1]) + 1:
        return None
    surplus = list(pair_after[1])
    for name in pair_before[1]:
        if name not in surplus:
            return None
        surplus.remove(name)
    if len(surplus) != 1 or surplus[0] not in permitted:
        return None
    return surplus[0]


def comment_block_above(source: str, anchor: str) -> set[str]:
    """Stripped `#:` lines in the contiguous block immediately above `anchor`.

    Structural, not textual: the block must sit directly on top of the param
    container, so a `#:` line elsewhere in the file is not silently permitted.
    """
    pattern = re.compile(anchor)
    lines = source.splitlines()
    for index, line in enumerate(lines):
        if not pattern.search(line):
            continue
        block: set[str] = set()
        cursor = index - 1
        while cursor >= 0 and lines[cursor].strip().startswith("#:"):
            block.add(lines[cursor].strip())
            cursor -= 1
        return block
    return set()


#: Any single- or double-quoted string literal on one source line.
_STRING_LITERAL_RE = re.compile(r"\"[^\"]*\"|'[^']*'")


def string_literals(line: str) -> list[str]:
    """Every quoted string on `line`, in order, without its quotes."""
    return [match.group(0)[1:-1] for match in _STRING_LITERAL_RE.finditer(line)]


def line_skeleton(line: str) -> str:
    """`line` with every string literal, all whitespace and all commas removed.

    Two lines with the same skeleton differ ONLY in their string literals — no
    operator, no identifier, no bracket and no call shape changed between them.
    That is what makes the enumeration-extension permission below narrow enough
    to grant.
    """
    stripped = _STRING_LITERAL_RE.sub("", line)
    return re.sub(r"[\s,]+", "", stripped)


def is_forced_enumeration_extension(
    added: str, deleted: str, new_names: frozenset[str]
) -> bool:
    """Is (`deleted` -> `added`) a one-member extension of a backend enumeration?

    Granted by D-IMPL-92's 2026-08-08 second correction, and deliberately as
    tight as the `#:` comment-block permission it mirrors. ALL of:

    * the two lines are identical once every string literal is removed — so
      nothing but the literals changed;
    * the added line's literals are the deleted line's literals plus exactly
      one more; and
    * that one more is the new backend's name, derived from the `backend`
      Literal rather than hard-coded.

    Anything else in a conformance suite is still a finding.
    """
    if line_skeleton(added) != line_skeleton(deleted):
        return False
    before = string_literals(deleted)
    after = string_literals(added)
    if len(after) != len(before) + 1:
        return False
    surplus = list(after)
    for name in before:
        if name not in surplus:
            return False
        surplus.remove(name)
    return len(surplus) == 1 and surplus[0] in new_names


def new_backend_names(root: pathlib.Path, base: str) -> frozenset[str]:
    """Backend names this phase ADDED to the `backend` Literal.

    Derived from the mechanism (the enumeration itself), never hard-coded — the
    same discipline as `check_backend_names_kept`.
    """
    base_source = blob(root, base, LITERAL_SOURCE) or ""
    head_source = (root / LITERAL_SOURCE).read_text(encoding="utf-8")
    if not base_source:
        return frozenset()
    return literal_backend_names(head_source) - literal_backend_names(base_source)


def diff_lines(root: pathlib.Path, base: str, path: str) -> tuple[list[str], list[str]]:
    """(added, deleted) content lines for `path`, from a -U0 unified diff."""
    added: list[str] = []
    deleted: list[str] = []
    for line in git(root, "diff", "-U0", f"{base}...HEAD", "--", path).splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            added.append(line[1:])
        elif line.startswith("-"):
            deleted.append(line[1:])
    return added, deleted


def nested_imports(source: str, path: pathlib.Path, module: str) -> list[int]:
    """Line numbers of function/method-scoped imports of `module`."""
    tree = read_tree(source, path)
    hits: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for child in ast.walk(node):
            names: list[str] = []
            if isinstance(child, ast.Import):
                names = [a.name for a in child.names]
            elif isinstance(child, ast.ImportFrom):
                names = [child.module or ""]
            if any(n == module or n.startswith(module + ".") for n in names):
                hits.append(child.lineno)
    return hits


# --------------------------------------------------------------------------
# The checks
# --------------------------------------------------------------------------


def check_self_tree(root: pathlib.Path, evidence: list[str]) -> list[str]:
    """DI-15.2-04: fail if the imported `ccf` is not this worktree's `ccf`.

    The recorded trap: a GSD worktree's `.venv` symlinks to the main
    checkout's venv, and the editable finder's MAPPING is hard-coded to the
    main checkout's `src/ccf`. A bare invocation therefore imports the MAIN
    CHECKOUT's source, and every conclusion drawn is wrong in the same
    direction. This single check would have caught it at first occurrence.
    """
    findings: list[str] = []
    try:
        import ccf  # noqa: PLC0415  (deliberate: the import IS the assertion)

        ccf_file = pathlib.Path(ccf.__file__ or "").resolve()
    except Exception as exc:  # pragma: no cover - environment failure
        evidence.append(f"  imported ccf.__file__     : <import failed: {exc}>")
        return [
            format_finding(
                pathlib.Path("tools/gates/gate_15_3.py"),
                0,
                RULE_SELF_TREE,
                f"could not import ccf to verify the self-tree assertion: {exc}."
                " Run through `make gate-15.3`, which carries $(ENV)",
            )
        ]

    evidence.append(f"  imported ccf.__file__     : {ccf_file}")
    if not str(ccf_file).startswith(str(root.resolve()) + "/"):
        findings.append(
            format_finding(
                pathlib.Path(str(ccf_file)),
                0,
                RULE_SELF_TREE,
                f"the imported `ccf` lives OUTSIDE this toplevel ({root}). This is"
                " DI-15.2-04: the worktree's .venv points at the main checkout's"
                " editable install, so the measurement describes code this tree did"
                " not change. Invoke via `make gate-15.3` (it carries"
                " PYTHONPATH=src:runtime)",
            )
        )
    return findings


def check_tree_clean(root: pathlib.Path, evidence: list[str]) -> list[str]:
    """A dirty tree makes the recorded measurement unreproducible."""
    porcelain = git(root, "status", "--porcelain").strip()
    evidence.append(
        f"  working tree              : {'CLEAN' if not porcelain else 'DIRTY'}"
    )
    if not porcelain:
        return []
    entries = [line.strip() for line in porcelain.splitlines()]
    return [
        format_finding(
            root,
            0,
            RULE_DIRTY_TREE,
            "`git status --porcelain` is non-empty, so the three-dot diff this"
            " gate measures does not describe the tree on disk. Commit or revert"
            f" first. Entries: {'; '.join(entries[:8])}"
            + (" ..." if len(entries) > 8 else ""),
        )
    ]


def check_base_resolution(
    root: pathlib.Path, base: str, changes: Sequence[Change]
) -> list[str]:
    """Guard against a mis-resolved base producing a vacuous pass."""
    findings: list[str] = []
    if not git_ok(root, "merge-base", "--is-ancestor", base, "HEAD"):
        findings.append(
            format_finding(
                root,
                0,
                RULE_BASE_RESOLUTION,
                f"the base ref {base} is not an ancestor of HEAD; the three-dot"
                " diff below is not this phase's change surface",
            )
        )
    if not any(c.path == ADAPTER_MODULE for c in changes):
        findings.append(
            format_finding(
                pathlib.Path(ADAPTER_MODULE),
                0,
                RULE_BASE_RESOLUTION,
                f"the measured surface does not contain {ADAPTER_MODULE}. Either"
                " the base ref resolved to something that already contains the"
                " phase (a gate measuring an empty diff passes everything, which"
                " is the one failure mode this gate must never have), or the"
                " adapter is missing",
            )
        )
    return findings


def check_paths(changes: Sequence[Change]) -> list[str]:
    """Layer-2 check (1) plus the single-owner deny evaluated ahead of it."""
    findings: list[str] = []
    for change in changes:
        if change.path in SINGLE_OWNER_DENY:
            findings.append(
                format_finding(
                    pathlib.Path(change.path),
                    0,
                    RULE_SINGLE_OWNER,
                    SINGLE_OWNER_DENY[change.path],
                )
            )
            continue  # a narrower pre-filter, not an early return from the run
        entry = allowed_for(change.path)
        if entry is not None and entry.append_only and change.deleted > 0:
            findings.append(
                format_finding(
                    pathlib.Path(change.path),
                    0,
                    RULE_APPEND_ONLY,
                    f"deleted {change.deleted} line(s). This path is allowlisted"
                    " APPEND-ONLY: it may grow, never shrink. The"
                    " D-IMPL-86/-87/-92 discipline is that a correction is"
                    " appended and dated rather than edited into the entry it"
                    " corrects, so the reasoning at each point in time survives;"
                    " a deletion is rewritten history. Append a new dated entry"
                    " instead. (This bound is what keeps the allowlist entry a"
                    " check rather than a hole.)",
                )
            )
            continue
        if entry is None:
            findings.append(
                format_finding(
                    pathlib.Path(change.path),
                    0,
                    RULE_PATH_ALLOWLIST,
                    f"changed (+{change.added}/-{change.deleted}) but is not in the"
                    " D-IMPL-92 permitted-change surface. If this path is genuinely"
                    " required to add a substrate, that is a D-IMPL question for"
                    " Dave — NOT an edit to this allowlist. Widening the allowlist"
                    " to make the gate pass converts the check back into the"
                    " narration D-10 exists to prevent",
                )
            )
    return findings


def check_backend_names_kept(root: pathlib.Path, base: str) -> list[str]:
    """Layer-2 check (2): no pre-existing backend name removed."""
    base_literal = blob(root, base, LITERAL_SOURCE)
    if base_literal is None:
        return [
            format_finding(
                pathlib.Path(LITERAL_SOURCE),
                0,
                RULE_BACKEND_REMOVED,
                f"could not read {LITERAL_SOURCE} at {base}; the check could not run",
            )
        ]
    names = literal_backend_names(base_literal)
    if not names:
        return [
            format_finding(
                pathlib.Path(LITERAL_SOURCE),
                0,
                RULE_BACKEND_REMOVED,
                "could not locate the `backend` Literal in the base ref; the"
                " pre-existing backend names could not be derived, so the check"
                " could not run. Loud beats silent",
            )
        ]

    findings: list[str] = []
    for path in ENUMERATION_FILES:
        base_source = blob(root, base, path)
        if base_source is None:
            continue
        head_source = (root / path).read_text(encoding="utf-8")
        for name in sorted(names):
            # Only names the file actually carried at the base ref are in
            # scope. The three registration files spell the enumeration
            # differently — `artifacts.py` and `manifest.py` carry quoted
            # `Literal` members, `boot.py` carries them as argument names
            # (`mongo_uri`) and as docstring prose — so the check asks the
            # base blob what it had rather than assuming a quoting form.
            if name not in base_source:
                continue
            if name not in head_source:
                findings.append(
                    format_finding(
                        pathlib.Path(path),
                        0,
                        RULE_BACKEND_REMOVED,
                        f"the pre-existing backend name {name!r} was present at"
                        " the base ref and no longer appears. Adding a substrate"
                        " extends an enumeration; removing a member of it is a"
                        " mechanism change. (Deletions are NOT themselves a"
                        " violation — the mongo landing deleted 11 lines of"
                        " rewritten docstring prose.)",
                    )
                )
    return findings


def check_budgets(changes: Sequence[Change], evidence: list[str]) -> list[str]:
    """Layer-2 check (3): per-file added-line budgets, printed with baselines."""
    findings: list[str] = []
    by_path = {c.path: c for c in changes}
    evidence.append("")
    evidence.append("  Tier-B budgets (added lines; --numstat FIRST column only):")
    for path, budget in BUDGETS.items():
        added = by_path[path].added if path in by_path else 0
        evidence.append(
            f"    {path}: added={added} budget={budget.limit}"
            f" (mongo baseline: {budget.mongo_baseline})"
        )
        if added > budget.limit:
            findings.append(
                format_finding(
                    pathlib.Path(path),
                    0,
                    RULE_BUDGET,
                    f"added={added} exceeds budget={budget.limit}"
                    f" (mongo baseline: {budget.mongo_baseline}). A change beyond"
                    " budget in a registration file is the refactor the claim"
                    " denies. NOTE: the budget is an ADMITTED PROXY for"
                    " 'extension, not modification' — if it fired on a change"
                    " that really is an extension, the ruling says tighten it to"
                    " a direct AST check, not to raise it",
                )
            )
    return findings


def check_schema_consistency(root: pathlib.Path, evidence: list[str]) -> list[str]:
    """`docs/schemas/...json` carries no budget; assert it matches the Literal.

    D-IMPL-92 words the method as "re-run `make schemas` and require a clean
    tree". This gate asserts the same fact WITHOUT mutating the tree, because
    a gate whose first check is "the working tree must be clean" must not
    itself dirty it. The direct comparison is deterministic and side-effect
    free, and full byte-for-byte regeneration drift is already covered by the
    always-on assertion at
    tests/cli/test_schema_export.py::test_each_committed_schema_is_its_class_byte_for_byte,
    which `make test` runs on every commit — cited here for the same reason
    CINV-02 is cited rather than re-implemented.
    """
    import json  # noqa: PLC0415  (local: only this check needs it)

    schema_path = "docs/schemas/ccf.deployment-manifest.json"
    schema = json.loads((root / schema_path).read_text(encoding="utf-8"))
    enum = frozenset(schema["properties"]["backend"]["enum"])
    literal = literal_backend_names(
        (root / LITERAL_SOURCE).read_text(encoding="utf-8")
    )
    evidence.append("")
    evidence.append(
        f"  schema `backend` enum     : {sorted(enum)}"
        f" == artifacts.py Literal {sorted(literal)}"
        f" -> {'consistent' if enum == literal else 'INCONSISTENT'}"
    )
    if enum == literal:
        return []
    return [
        format_finding(
            pathlib.Path(schema_path),
            0,
            RULE_SCHEMA_CONSISTENCY,
            f"the generated `backend` enum {sorted(enum)} does not match the"
            f" `backend` Literal {sorted(literal)} in {LITERAL_SOURCE}."
            " Run `make schemas`",
        )
    ]


def check_writer_module_level(
    root: pathlib.Path,
    base: str,
    base_source: str,
    head_source: str,
    path: pathlib.Path,
    added_defs: Sequence[str],
    evidence: list[str],
    recorded: list[str],
) -> list[str]:
    """The module-level half of layer-2 check (4) — WR-09's fix.

    HEAD's module-level statements must be an ordered SUPERSEQUENCE of the
    base's: every pre-existing statement still present, unmodified, in order.
    Additions are free — this is Tier A, and a new substrate's query-string
    constants have nowhere else to live under CINV-02.

    A base statement that fails to match does NOT consume the cursor, so one
    modified constant reports as one finding rather than cascading into every
    statement below it.
    """
    base_stmts = module_level_statements(base_source, path)
    head_stmts = module_level_statements(head_source, path)
    head_dumps = [ast.dump(node) for node in head_stmts]

    # The names the companion permission may admit, DERIVED rather than listed:
    # a top-level definition this phase ADDED to this module, whose name begins
    # with a backend name this phase added to the `backend` Literal.
    new_names = new_backend_names(root, base)
    permitted = frozenset(
        name
        for name in added_defs
        if any(name.lower().startswith(backend.lower()) for backend in new_names)
    )

    findings: list[str] = []
    companions: list[str] = []
    unmatched: list[ast.stmt] = []
    cursor = 0
    for stmt in base_stmts:
        dump = ast.dump(stmt)
        matched = False
        for index in range(cursor, len(head_dumps)):
            if head_dumps[index] == dump:
                cursor = index + 1
                matched = True
                break
        if matched:
            continue
        for index in range(cursor, len(head_stmts)):
            name = bounded_name_addition(stmt, head_stmts[index], permitted)
            if name is None:
                continue
            pair = name_collection(stmt)
            target = pair[0] if pair is not None else "<unknown>"
            companions.append(f"{WRITER_MODULE_PATH}: {target} gained {name!r}")
            cursor = index + 1
            matched = True
            break
        if not matched:
            unmatched.append(stmt)

    evidence.append(
        f"  _writer.py module level   : {len(base_stmts)} -> {len(head_stmts)}"
        f" statements; unmatched={len(unmatched)}"
        f" bounded-companions={len(companions)}"
        f" (permitted companion names: {sorted(permitted)})"
    )
    for line in companions:
        evidence.append(f"      companion + {line}")
        recorded.append(line)

    if len(companions) > 1:
        findings.append(
            format_finding(
                path,
                0,
                RULE_WRITER_AST,
                f"{len(companions)} module-level companion additions; the"
                " 2026-08-08 FOURTH correction permits exactly ONE — a single"
                " string collection gaining a single name, and that name the new"
                " backend's. More than one is a D-IMPL question for Dave, not a"
                " reason to widen the permission",
            )
        )
    for stmt in unmatched:
        findings.append(
            format_finding(
                path,
                getattr(stmt, "lineno", 0),
                RULE_WRITER_AST,
                f"the pre-existing module-level {type(stmt).__name__} statement at"
                f" base line {getattr(stmt, 'lineno', 0)} was MODIFIED or REMOVED."
                " This file is Tier A with NO line budget, so its module-level"
                " constants are checked structurally instead: existing statements"
                " may be added to but never rewritten. The ONE permitted companion"
                " is a flat string collection gaining exactly one name, and that"
                " name a new top-level definition of the new backend's"
                f" (permitted here: {sorted(permitted)})",
            )
        )
    return findings


def check_writer_ast(
    root: pathlib.Path, base: str, evidence: list[str], recorded: list[str]
) -> list[str]:
    """Layer-2 check (4): `_writer.py` may only GAIN, never change what it had.

    Two halves, and the second was missing until the 2026-08-08 FOURTH
    correction:

    * **Definitions.** Only NEW top-level classes and functions may appear;
      every pre-existing one must be byte- and AST-identical.
    * **Module level.** Every pre-existing module-level statement — imports,
      `__all__`, module constants, the per-backend query-string constants —
      must still be present, unmodified, and in order. New ones may be added
      freely (this file is Tier A: a new substrate's constants have nowhere
      else to go). Review finding WR-09 recorded the gap: without this half, a
      Tier-A file with **no line budget** could have an existing module
      constant rewritten and pass every check the gate ran.

    ONE bounded companion is permitted at module level, and it is recorded like
    the two conformance companions rather than merely allowed: `__all__` (or
    any flat string collection) may gain **exactly one** name, and that name
    must be a new top-level definition in this same module whose name begins
    with a backend name this phase added to the `backend` `Literal`. See
    `bounded_name_addition`. Measured before granting: at base `96f54c5` the
    module carried 33 module-level statements and HEAD carries 51, with exactly
    one base statement unmatched — `__all__`, which gained `FlureeGraphWriter`.
    """
    base_source = blob(root, base, WRITER_MODULE_PATH)
    if base_source is None:
        return [
            format_finding(
                pathlib.Path(WRITER_MODULE_PATH),
                0,
                RULE_WRITER_AST,
                f"could not read {WRITER_MODULE_PATH} at {base}",
            )
        ]
    head_source = (root / WRITER_MODULE_PATH).read_text(encoding="utf-8")
    path = pathlib.Path(WRITER_MODULE_PATH)
    before = top_level_defs(base_source, path)
    after = top_level_defs(head_source, path)

    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    # Two comparisons, deliberately. `ast.dump()` is the semantic one D-IMPL-92
    # names. The exact source segment is the second, because a comment inside an
    # existing body does not appear in the AST at all — a body edit that says
    # something new about the code while dumping identically would otherwise
    # walk straight through the check. Comparing segments (rather than dumping
    # with `include_attributes=True`) catches it without making every
    # pre-existing definition "modified" the moment a line is inserted above it.
    modified = sorted(
        name
        for name in set(before) & set(after)
        if ast.dump(before[name]) != ast.dump(after[name])
        or ast.get_source_segment(base_source, before[name])
        != ast.get_source_segment(head_source, after[name])
    )
    evidence.append("")
    evidence.append(
        f"  _writer.py                : {len(base_source.splitlines())} ->"
        f" {len(head_source.splitlines())} lines;"
        f" added={added} removed={removed} modified={modified}"
    )

    findings: list[str] = []
    findings += check_writer_module_level(
        root, base, base_source, head_source, path, added, evidence, recorded
    )
    for name in modified:
        kind = (
            "semantically"
            if ast.dump(before[name]) != ast.dump(after[name])
            else "textually (comment or formatting inside the body)"
        )
        findings.append(
            format_finding(
                path,
                after[name].lineno,
                RULE_WRITER_AST,
                f"the pre-existing top-level definition {name!r} was MODIFIED"
                f" {kind}. Only new classes and functions may appear here; the"
                f" expected additions are {sorted(WRITER_EXPECTED_ADDITIONS)}."
                " This is the check that also forbids splitting _writer.py into a"
                " package: a split relocates every existing definition, so the"
                " gate would fail on the phase's own refactor — which is exactly"
                " why 15.2 close-review advisory A5 stays CARRIED, not actioned",
            )
        )
    for name in removed:
        findings.append(
            format_finding(
                path,
                0,
                RULE_WRITER_AST,
                f"the pre-existing top-level definition {name!r} was REMOVED",
            )
        )
    for name in added:
        if name not in WRITER_EXPECTED_ADDITIONS:
            findings.append(
                format_finding(
                    path,
                    after[name].lineno,
                    RULE_WRITER_AST,
                    f"unexpected new top-level definition {name!r}; this phase"
                    f" expects only {sorted(WRITER_EXPECTED_ADDITIONS)}",
                )
            )
    return findings


def check_conformance(
    root: pathlib.Path,
    base: str,
    changes: Sequence[Change],
    evidence: list[str],
    recorded: list[str],
) -> list[str]:
    """One added `pytest.param` line, plus TWO bounded companion permissions.

    Neither companion is a loophole; both exist because the param addition is
    not self-contained in the file it lands in, and pretending otherwise would
    buy a tidy line count with a false file.

    * **The `#:` comment block** (first correction, 2026-08-08).
      `test_substrate_differential.py` names the container backends explicitly,
      so a fluree addition cannot be "one line, zero deleted" without leaving
      the comment stating something false.
    * **One forced enumeration extension** (second correction, 2026-08-08).
      `test_graphstore.py` guards its fixture on a set literal of backend
      names; without the new name in that set the added param raises
      `NotImplementedError`. That file has no `#:` block, so the first
      permission cannot reach it. See `is_forced_enumeration_extension` for
      how narrowly this is bounded.

    Both companions are **recorded**: every permitted non-param line is
    appended to `recorded` and must appear in the gate package once that
    package exists (`check_recorded_in_package`).
    """
    findings: list[str] = []
    new_names = new_backend_names(root, base)
    touched = {c.path for c in changes}
    evidence.append("")
    evidence.append(f"  Conformance suites (new backend name(s): {sorted(new_names)}):")
    for path, anchor in CONFORMANCE_SUITES.items():
        if path not in touched:
            evidence.append(f"    {path}: unchanged")
            findings.append(
                format_finding(
                    pathlib.Path(path),
                    0,
                    RULE_CONFORMANCE,
                    "no fluree param was added; the suite does not run against"
                    " the new substrate",
                )
            )
            continue

        base_source = blob(root, base, path) or ""
        head_source = (root / path).read_text(encoding="utf-8")
        base_block = comment_block_above(base_source, anchor)
        head_block = comment_block_above(head_source, anchor)
        added, deleted = diff_lines(root, base, path)

        param_added = [line for line in added if CONFORMANCE_PARAM_RE.search(line)]
        param_deleted = [line for line in deleted if CONFORMANCE_PARAM_RE.search(line)]
        comment_added = [
            line
            for line in added
            if not CONFORMANCE_PARAM_RE.search(line) and line.strip() in head_block
        ]
        comment_deleted = [
            line
            for line in deleted
            if not CONFORMANCE_PARAM_RE.search(line) and line.strip() in base_block
        ]

        # What is left once the param line and the `#:` block are accounted
        # for. The enumeration permission is applied to THIS residue only, and
        # pairwise: an added line is forgiven if and only if some remaining
        # deleted line is the same line minus exactly the new backend's name.
        residue_added = [
            line
            for line in added
            if line not in param_added and line not in comment_added
        ]
        residue_deleted = [
            line
            for line in deleted
            if line not in param_deleted and line not in comment_deleted
        ]
        enum_added: list[str] = []
        enum_deleted: list[str] = []
        for candidate in list(residue_added):
            match = next(
                (
                    other
                    for other in residue_deleted
                    if other not in enum_deleted
                    and is_forced_enumeration_extension(candidate, other, new_names)
                ),
                None,
            )
            if match is not None:
                enum_added.append(candidate)
                enum_deleted.append(match)

        other_added = [line for line in residue_added if line not in enum_added]
        other_deleted = [line for line in residue_deleted if line not in enum_deleted]

        evidence.append(
            f"    {path}: param+={len(param_added)} param-={len(param_deleted)}"
            f" comment-block+={len(comment_added)} comment-block-={len(comment_deleted)}"
            f" enum-extension+={len(enum_added)} enum-extension-={len(enum_deleted)}"
            f" other+={len(other_added)} other-={len(other_deleted)}"
        )
        for line in comment_added:
            evidence.append(f"      comment + {line.strip()}")
            recorded.append(line.strip())
        for line in comment_deleted:
            evidence.append(f"      comment - {line.strip()}")
        for line in enum_added:
            evidence.append(f"      enum-extension + {line.strip()}")
            recorded.append(line.strip())
        for line in enum_deleted:
            evidence.append(f"      enum-extension - {line.strip()}")

        if len(enum_added) > 1:
            findings.append(
                format_finding(
                    pathlib.Path(path),
                    0,
                    RULE_CONFORMANCE,
                    f"{len(enum_added)} enumeration extensions in one suite; the"
                    " 2026-08-08 second correction permits exactly ONE forced"
                    " one-line extension beside the param addition",
                )
            )

        if len(param_added) != 1:
            findings.append(
                format_finding(
                    pathlib.Path(path),
                    0,
                    RULE_CONFORMANCE,
                    f"expected exactly ONE added line matching"
                    f' `pytest.param("fluree", marks=pytest.mark.fluree)`,'
                    f" found {len(param_added)}",
                )
            )
        if param_deleted:
            findings.append(
                format_finding(
                    pathlib.Path(path),
                    0,
                    RULE_CONFORMANCE,
                    f"a `pytest.param(\"fluree\", ...)` line was DELETED"
                    f" ({len(param_deleted)}x)",
                )
            )
        for line in other_added + other_deleted:
            sign = "+" if line in other_added else "-"
            findings.append(
                format_finding(
                    pathlib.Path(path),
                    0,
                    RULE_CONFORMANCE,
                    f"change outside the permitted shapes ({sign}{line.strip()!r})."
                    " D-IMPL-92 as corrected permits, per conformance suite, ONE"
                    " added `pytest.param` line PLUS edits confined to the `#:`"
                    " comment block immediately above the param tuple PLUS one"
                    " forced one-line extension of a backend-name enumeration"
                    " (a set/tuple/list literal that gained exactly the new"
                    " backend's name and changed in no other way), and nothing"
                    " else. A change that is genuinely forced by adding a substrate"
                    " but is none of those is a D-IMPL question for Dave — not a"
                    " reason to loosen this rule",
                )
            )
    return findings


def check_recorded_in_package(
    root: pathlib.Path, recorded: Sequence[str], evidence: list[str]
) -> list[str]:
    """Both conformance companions must be RECORDED, not merely permitted.

    D-IMPL-92's first correction requires the `#:` comment change be "recorded
    in the gate package"; the second correction requires the same of the
    enumeration extension. This is that requirement, and it is what stops the
    two permissions from becoming quiet exemptions.

    **Armed by existence**, exactly like the corpus rule: the gate package is
    written by this same plan's final task, so until it exists the gate's own
    evidence block IS the record (every permitted line is printed verbatim
    above, which is what the package is assembled from). From the moment the
    package lands, the assertion is live and stays live.
    """
    evidence.append("")
    package = root / GATE_PACKAGE
    if not recorded:
        evidence.append("  recorded companions       : none to record")
        return []
    if not package.is_file():
        evidence.append(
            f"  recorded companions       : {len(recorded)} line(s) printed above;"
            " gate package not yet written, so the evidence block is the record"
            " (this assertion arms itself when the package lands)"
        )
        return []

    text = re.sub(r"\s+", " ", package.read_text(encoding="utf-8"))
    missing = [line for line in recorded if re.sub(r"\s+", " ", line) not in text]
    evidence.append(
        f"  recorded companions       : {len(recorded) - len(missing)}"
        f"/{len(recorded)} line(s) present in the gate package"
    )
    return [
        format_finding(
            pathlib.Path(GATE_PACKAGE),
            0,
            RULE_CONFORMANCE,
            f"a permitted conformance companion is not recorded here: {line!r}."
            " Both companion permissions (the `#:` comment block and the forced"
            " enumeration extension) are granted ON CONDITION that the change is"
            " written down — an unrecorded one is a quiet exemption, which is"
            " what D-IMPL-92 grants permissions in order to avoid",
        )
        for line in missing
    ]


def check_corpus(
    root: pathlib.Path, changes: Sequence[Change], evidence: list[str]
) -> list[str]:
    """Recorded, not blocked — and the distinction is implemented literally.

    D-11's stated worry is that a gate failing on ANY corpus change would
    pressure an executor away from adding a fixture that ought to be added. A
    gate that fails on an UNJUSTIFIED one creates the opposite pressure. It is
    one `if`; this is that `if`.
    """
    corpus = [c for c in changes if c.path == CORPUS_PATH]
    evidence.append("")
    if not corpus:
        evidence.append("  corpus verdict            : unchanged — no addition needed")
        return []

    change = corpus[0]
    evidence.append(
        f"  corpus verdict            : CHANGED (+{change.added}/-{change.deleted})"
        " — justification required in the gate package"
    )
    package = root / GATE_PACKAGE
    if not package.is_file():
        return [
            format_finding(
                pathlib.Path(CORPUS_PATH),
                0,
                RULE_CORPUS,
                f"changed (+{change.added}/-{change.deleted}) but the gate package"
                f" {GATE_PACKAGE} does not exist. A corpus addition is permitted"
                " and must be RECORDED: (a) what shape was added, (b) why it was"
                " needed, (c) the D-11 classification — 'exposes a gap in the 15.2"
                " corpus' vs 'a Fluree quirk'",
            )
        ]

    text = package.read_text(encoding="utf-8")
    lines = text.splitlines()
    section: list[str] = []
    inside = False
    for line in lines:
        if CORPUS_SECTION_RE.match(line):
            inside = True
            continue
        if inside and re.match(r"^#{1,6}\s+", line):
            break
        if inside:
            section.append(line)
    body = "\n".join(section)

    missing: list[str] = []
    if not section:
        missing.append("a heading naming the corpus verdict")
    if not CORPUS_SHAPE_RE.search(body):
        missing.append("(a) what shape was added")
    if not CORPUS_WHY_RE.search(body):
        missing.append("(b) why it was needed")
    if not CORPUS_CLASSIFICATION_RE.search(body):
        missing.append(
            "(c) the D-11 classification — 'exposes a gap in the 15.2 corpus'"
            " or 'a Fluree quirk'"
        )
    if not missing:
        evidence.append(
            "                              justification present in the gate"
            " package — the entry IS the finding"
        )
        return []
    return [
        format_finding(
            pathlib.Path(CORPUS_PATH),
            0,
            RULE_CORPUS,
            f"changed (+{change.added}/-{change.deleted}) with an incomplete"
            f" justification in {GATE_PACKAGE}. Missing: {'; '.join(missing)}."
            " 'The SDK bent' is a failure; 'the corpus grew' may be a finding —"
            " and the difference has to be written down",
        )
    ]


def check_frozen(root: pathlib.Path, base: str, evidence: list[str]) -> list[str]:
    """Free assertions: the byte-frozen paths, as script rather than prose."""
    findings: list[str] = []
    evidence.append("")
    for path in FROZEN_PATHS:
        clean = git_ok(root, "diff", "--exit-code", f"{base}...HEAD", "--", path)
        evidence.append(
            f"  frozen {path:<26}: {'untouched' if clean else 'CHANGED'}"
        )
        if not clean:
            findings.append(
                format_finding(
                    pathlib.Path(path),
                    0,
                    RULE_FROZEN,
                    "byte-frozen across the whole phase. D-11 makes the"
                    " GRAPH_QUERY_SEMANTICS freeze a hard line (amendments go in"
                    " the GQ-35 lane, line-number-neutral) and the 15.2 gate"
                    " asserted both perf paths untouched",
                )
            )
    return findings


def check_lint(root: pathlib.Path, evidence: list[str]) -> list[str]:
    """Cite CINV-02 rather than re-implement it: assert the lint gate is green."""
    proc = subprocess.run(
        [sys.executable, "-m", "tools.lints", "--all"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    evidence.append("")
    evidence.append(
        f"  tools.lints --all         : exit {proc.returncode}"
        f" (cites {CITED_LINT_RULE} — write confinement to ccf.graph._writer,"
        " NOT re-implemented here)"
    )
    if proc.returncode == 0:
        return []
    return [
        format_finding(
            root,
            0,
            RULE_LINT,
            f"`python -m tools.lints --all` exited {proc.returncode}. The"
            f" {CITED_LINT_RULE} rule is the standing invariant that proves no"
            " *GraphWriter/*GraphTxn class exists outside ccf.graph._writer; this"
            " gate cites it rather than re-implementing it, so a red lint is a red"
            f" gate. Output: {proc.stdout.strip()[:400]}",
        )
    ]


def check_packaging_absences(
    root: pathlib.Path, base: str, evidence: list[str]
) -> list[str]:
    """The seven SUBQ-14 absences, each named and each recorded.

    SUBQ-14's evidence is largely negative — a substrate that needed no
    packaging accommodation. An absence nobody asserted is an absence nobody
    can rely on, so each is a check.
    """
    findings: list[str] = []
    results: list[tuple[str, bool, str]] = []

    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    base_pyproject_text = blob(root, base, "pyproject.toml") or ""
    base_pyproject = tomllib.loads(base_pyproject_text) if base_pyproject_text else {}

    # 1 — no optional-dependency entry naming fluree.
    extras = pyproject.get("project", {}).get("optional-dependencies", {})
    offending = sorted(
        key
        for key, deps in extras.items()
        if "fluree" in key.lower()
        or any("fluree" in str(dep).lower() for dep in deps)
    )
    results.append(
        (
            "no [project.optional-dependencies] entry naming fluree",
            not offending,
            f"found {offending}" if offending else "",
        )
    )

    # 2 — no mypy override naming fluree or httpx added by this phase.
    def override_modules(doc: dict[str, object]) -> set[str]:
        tool = doc.get("tool", {})
        mypy = tool.get("mypy", {}) if isinstance(tool, dict) else {}
        overrides = mypy.get("overrides", []) if isinstance(mypy, dict) else []
        names: set[str] = set()
        for override in overrides if isinstance(overrides, list) else []:
            module = override.get("module") if isinstance(override, dict) else None
            if isinstance(module, str):
                names.add(module)
            elif isinstance(module, list):
                names.update(str(m) for m in module)
        return names

    new_overrides = sorted(
        name
        for name in override_modules(pyproject) - override_modules(base_pyproject)
        if "fluree" in name.lower() or "httpx" in name.lower()
    )
    results.append(
        (
            "no [[tool.mypy.overrides]] block naming fluree or httpx added",
            not new_overrides,
            f"found {new_overrides}" if new_overrides else "",
        )
    )

    # 3 — no lazy in-constructor driver import.
    adapter_source = (root / ADAPTER_MODULE).read_text(encoding="utf-8")
    lazy = nested_imports(adapter_source, pathlib.Path(ADAPTER_MODULE), "httpx")
    results.append(
        (
            "no lazy in-constructor driver import (httpx is module-level)",
            not lazy,
            f"function-scoped `import httpx` at lines {lazy}" if lazy else "",
        )
    )

    # 4 — no deferred module import in the boot branch.
    boot_source = (root / BOOT_PATH).read_text(encoding="utf-8")
    deferred = nested_imports(
        boot_source, pathlib.Path(BOOT_PATH), "ccf.graph.backends.fluree"
    )
    results.append(
        (
            "no deferred module import in the boot fluree branch",
            not deferred,
            f"function-scoped import at lines {deferred}" if deferred else "",
        )
    )

    # 5 — no `# noqa: PLC0415` added.
    base_boot = blob(root, base, BOOT_PATH) or ""
    added_noqa = (
        adapter_source.count(PLC0415) > 0
        or boot_source.count(PLC0415) > base_boot.count(PLC0415)
    )
    results.append(
        (
            f"no `# noqa: {PLC0415}` added in the adapter or the boot branch",
            not added_noqa,
            (
                f"adapter={adapter_source.count(PLC0415)},"
                f" boot {base_boot.count(PLC0415)} -> {boot_source.count(PLC0415)}"
            )
            if added_noqa
            else "",
        )
    )

    # 6 — the ci.yml install line unchanged.
    def install_lines(text: str) -> list[str]:
        return [line.strip() for line in text.splitlines() if CI_INSTALL_RE.search(line)]

    base_ci = blob(root, base, CI_WORKFLOW) or ""
    head_ci = (root / CI_WORKFLOW).read_text(encoding="utf-8")
    ci_same = install_lines(base_ci) == install_lines(head_ci)
    results.append(
        (
            "no change to the ci.yml install line",
            ci_same,
            f"{install_lines(base_ci)} -> {install_lines(head_ci)}"
            if not ci_same
            else "",
        )
    )

    # 7 — the fluree marker carries no "requires the optional X extra" clause.
    marker = next(
        (
            line.strip()
            for line in (root / "pyproject.toml")
            .read_text(encoding="utf-8")
            .splitlines()
            if FLUREE_MARKER_RE.match(line)
        ),
        "",
    )
    marker_clean = bool(marker) and not OPTIONAL_EXTRA_CLAUSE_RE.search(marker)
    results.append(
        (
            'no "requires the optional `X` extra" clause in the fluree marker',
            marker_clean,
            marker if not marker_clean else "",
        )
    )

    evidence.append("")
    evidence.append("  Packaging absences (SUBQ-14 evidence, seven):")
    for index, (label, held, detail) in enumerate(results, 1):
        evidence.append(f"    {index}. {'ABSENT' if held else 'PRESENT'} — {label}")
        if not held:
            findings.append(
                format_finding(
                    pathlib.Path("pyproject.toml"),
                    0,
                    RULE_PACKAGING,
                    f"packaging absence {index} does NOT hold — {label}. {detail}."
                    " SUBQ-14's evidence is that this substrate needed no packaging"
                    " accommodation; a present accommodation is a real finding, not"
                    " a rule to relax",
                )
            )
    return findings


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.gates.gate_15_3",
        description=(
            "Phase 15.3 permitted-change-surface gate (D-IMPL-92). Blocking by"
            " design (D-07): nonzero exit on any finding, and no report-only"
            " mode exists."
        ),
    )
    parser.add_argument(
        "--base",
        default=PHASE_BASE,
        help=(
            "base ref for the three-dot diff (default: the pinned phase base"
            f" {PHASE_BASE})"
        ),
    )
    return parser


def run(root: pathlib.Path, base: str) -> tuple[list[str], list[str]]:
    """Run every check; return (evidence lines, findings). Never short-circuits."""
    evidence: list[str] = []
    findings: list[str] = []

    head = git(root, "rev-parse", "HEAD").strip()
    live_merge_base = git(root, "merge-base", "main", "HEAD").strip()
    evidence.append("gate-15.3 — Phase 15.3 permitted-change surface (D-IMPL-92)")
    evidence.append("")
    evidence.append("Evidence block (DI-15.2-04: prove which tree was measured)")
    evidence.append(f"  base ref (literal SHA)    : {base}")
    evidence.append(f"  git merge-base main HEAD  : {live_merge_base}")
    if live_merge_base != base:
        evidence.append(
            "                              (differs from the base ref: this"
            " phase's earlier waves are already merged into `main`, so the live"
            " merge-base has advanced to the phase's own work. The pinned SHA is"
            " the phase's true base — see PHASE_BASE.)"
        )
    evidence.append(f"  git rev-parse HEAD        : {head}")
    evidence.append(
        f"  git rev-parse --show-toplevel: {git(root, 'rev-parse', '--show-toplevel').strip()}"
    )

    findings += check_self_tree(root, evidence)
    findings += check_tree_clean(root, evidence)

    changes = measure(root, base)
    findings += check_base_resolution(root, base, changes)

    evidence.append("")
    evidence.append(
        f"  Measured surface: {len(changes)} paths,"
        " `git diff --numstat BASE...HEAD` (FIRST column = added; the `--stat`"
        " form of `git show` is never used — its right column is added+deleted)"
    )
    for change in changes:
        entry = allowed_for(change.path)
        tier = (
            "DENY"
            if change.path in SINGLE_OWNER_DENY
            else entry.tier if entry else "OUTSIDE"
        )
        evidence.append(
            f"    [{tier}] {change.status} +{change.added:<5} -{change.deleted:<5}"
            f" {change.path}"
        )

    findings += check_paths(changes)
    findings += check_backend_names_kept(root, base)
    findings += check_budgets(changes, evidence)
    findings += check_schema_consistency(root, evidence)
    recorded: list[str] = []
    findings += check_writer_ast(root, base, evidence, recorded)
    findings += check_conformance(root, base, changes, evidence, recorded)
    findings += check_recorded_in_package(root, recorded, evidence)
    findings += check_corpus(root, changes, evidence)
    findings += check_frozen(root, base, evidence)
    findings += check_lint(root, evidence)
    findings += check_packaging_absences(root, base, evidence)

    evidence.append("")
    evidence.append(
        "  LIMITS OF THIS CLAIM: this gate proves a fact about ONE diff. It is"
        " not a general property of the architecture, and the budgets are an"
        " admitted proxy for 'extension, not modification' (D-IMPL-92)."
    )
    return evidence, findings


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = pathlib.Path(
        subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )
    evidence, findings = run(root, args.base)

    for line in evidence:
        print(line)
    if findings:
        print("")
    for finding in findings:
        print(finding)
    sys.stdout.flush()

    if findings:
        print(
            f"\n{len(findings)} permitted-change-surface violation(s) against"
            " D-IMPL-92. Fix the DIFF — never the allowlist, the budgets, or the"
            " rules. A path genuinely required to add a substrate but outside the"
            " permitted surface is a D-IMPL question for Dave, not an edit to this"
            " file.",
            file=sys.stderr,
        )
        return 1
    print(
        "\ngate-15.3: the permitted-change surface holds. Adding a real substrate"
        " touched one new module, one writer class, and a bounded extension of the"
        " existing enumerations.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
