"""`python -m tools.lints` — the blocking CI gate for CINV-01/02/03/04/06 (D-07).

Walks the linted trees (`src/`, `runtime/`, `examples/`, `tests/`), derives
each file's dotted module name from its path, runs the selected checkers,
applies the D-08 allowlist to CINV-01 findings, prints what survives, and
exits nonzero if anything does. Not every rule runs over every tree — see
`RULE_TREE_SCOPE`.

Most checkers are **per-file AST** checkers, invoked once per Python module.
Two are **whole-tree** checkers, registered in `WHOLE_TREE_CHECKERS`, each
carrying its own tree scope and reporting in the same `path:line rule
message` format so the gate signal stays one exit code. `citations` is a
whole-tree **text** checker: a citation is a claim about a *second* file, so
it cannot be decided from one module's AST, and it lives in prose (Markdown,
YAML comments, docstrings) as much as in code. `hash-transparent-key`
(CINV-06, D-IMPL-243 amendments 1 and 2) is a whole-tree **AST** checker:
subclassing crosses files, so which classes are `CCFContract`s is a
tree-level fact; its universe is bounded by a committed base roster
(`tools/lints/hash_transparent_base_roster.json`, measured at `13bd250`)
rather than by a tree scope.

Exit code is the only gate signal. There is deliberately no report-only,
warning-only, or `--exit-zero` mode: D-07 requires the lints to block from the
first fabric commit, and a non-blocking mode is how an invariant quietly stops
being one. `--report` prints *additional* coverage detail alongside the
findings; it does not change the exit code and cannot suppress a finding.

No allowlist beyond CINV-01 (D-13)
----------------------------------

`apply_allowlist` runs for `no-hardcoding` and for nothing else. The two
D-IMPL-93 rules registered here — `backend-imports` and `substrate-names` —
take **no** allowlist, and the failure message below says so by naming CINV-01
as the only rule an `allowlist.yaml` entry can reach.

This is a deliberate deviation from D-IMPL-93's own wording, which says
`tools/lints/allowlist.yaml` governs exceptions to the new rules. It is
stricter, not looser, and Dave ruled it (D-13). Three reasons, each
independent: an allowlist entry matches on a sha256 fingerprint of the exact
offending *literal*, which an import rule structurally cannot produce;
`allowlist.yaml`'s header and `harness_imports.py` already both state that an
import restriction with exceptions is not an invariant; and a data-file
opt-out on a rule whose whole subject is "core names no adapter" would void
the invariant it exists to enforce. Carve-outs for those two rules are named
module-path constants in `backend_imports.py` and `substrate_names.py`,
reviewed with the code. Plan 15.4-12 records the same deviation in the gate
package.

Usage::

    python -m tools.lints --all
    python -m tools.lints --harness-imports --algorithmic
    python -m tools.lints --citations --report
"""

from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Callable, Iterator, Sequence

from tools.lints import (
    algorithmic,
    backend_imports,
    citations,
    harness_imports,
    hash_transparent_key,
    no_hardcoding,
    orchestration_imports,
    substrate_names,
)

#: Trees that are linted, and the package root each one contributes.
#: (directory, strip_prefix) — module names are derived relative to the root
#: that actually holds the package, so `src/ccf/x.py` is `ccf.x`.
#:
#: ``archive`` joined in plan ``23-03``, ahead of Phase 23's move of ten
#: condemned example trees into ``archive/examples/`` (``D-03``). Without it
#: the runner was measured EXITING 0 over the moved trees — 265 files leaving
#: CINV-01's reach because the walk stopped looking, which is precisely the
#: defect class Phase 22.1 was commissioned to close. Adding it here is
#: necessary and NOT sufficient: ``no-hardcoding`` names its own trees in
#: ``RULE_TREE_SCOPE`` below and had to gain the member there too.
#:
#: **The member is the top-level ``archive``, not ``archive/examples``, and the
#: asymmetry with plan 23-02 is deliberate.** These are tree names, not path
#: prefixes — ``run`` joins each to the repo base and derives module names
#: relative to it. For a LINT the inheriting default is the safe one: a future
#: ``archive/anything`` should be linted the day it appears. Contrast
#: ``tools/publish_scan.py::INCLUDE_ALLOWED_PREFIXES``, which took the NARROW
#: ``archive/examples/`` in plan 23-02, because a publication allowlist is
#: default-DENY and there inheritance is the unsafe direction. Both spellings
#: are reasoned at their own constant; neither is a slip to be tidied into
#: consistency. Guarded by ``tools/lints/tests/test_scope.py``.
LINTED_TREES: tuple[str, ...] = ("src", "runtime", "examples", "tests", "archive")

#: Per-rule tree scoping — the lint posture over ``/examples``, stated in
#: config rather than left to path accident (plan 08-01; 08-RESEARCH.md Open
#: Question 3). CINV-01 (No-Hardcoding) covers ``examples`` because CLAUDE.md
#: §6.4 applies the rule to ``/src``, ``/runtime``, and ``/examples`` alike.
#: CINV-02 (harness imports) is scoped OFF the examples tree: CLAUDE.md §7.3
#: words the invariant as "zero harness imports in **core**", and example 03
#: (harness portability) necessarily imports harness SDKs. The exemption is
#: this config surface — not an allowlist entry, and not merely a test
#: assertion. Rules absent from this mapping run over every linted tree.
#:
#: The ``harness-imports`` checker carries three rules under one AST walk —
#: ``cinv02-harness``, ``cinv02-graph-writer``, and ``cinv02-deployment-gates``
#: (the D-15A ban on ``ccf.deployment`` importing ``ccf.products.gates``). All
#: three share this checker's ``("src", "runtime")`` scope, which already covers
#: ``ccf.deployment``; the third rule needs no ``CHECKERS`` key of its own, and
#: naming it here keeps the config surface an honest description of what runs.
#:
#: CINV-01 also covers ``tests`` (D-IMPL-78, Dave, 2026-08-04; plan 15-04).
#: D-09 relocates the example CI assertions into ``tests/``, and those
#: assertions carry domain expectations read from ``expected:`` artifact
#: blocks. Without this scope the relocation would move domain values out of
#: a structural invariant's reach with every CI gate still green — a
#: CI-invisible weakening arrived at as a side effect of an ergonomics
#: change. The other three rules stay ``("src", "runtime")`` deliberately:
#: test modules exercising the harness adapters import harness SDKs and
#: would trip CINV-02, and the invariant is worded over core (CLAUDE.md
#: §7.3). As with ``/examples``, the exemption surface is this config file —
#: not an allowlist entry, and not merely a test assertion.
#:
#: ``backend-imports`` (CINV-02, D-IMPL-93 property (1); plan 15.4-07) takes
#: ``("src", "runtime")``, the same scope as the other import rules and for the
#: same reason — the invariant is worded over core. It is scoped OFF ``tests``
#: deliberately rather than by omission: a per-backend unit suite importing the
#: backend it is a unit suite *for* is the suite doing its job, not a core
#: module naming an adapter, and there are 45 such imports under ``tests``
#: today. ``runtime`` is IN scope and has zero violations, so including it
#: costs nothing and closes the seam a deployment-wiring module would otherwise
#: leave open. This rule's blind spot — a dynamic ``importlib.import_module``
#: — is stated in ``backend_imports.py`` and compensated by a test that scans
#: these same two trees, so the control is exactly as wide as the rule.
#:
#: ``substrate-names`` (CINV-04, D-IMPL-93 property (2); plan 15.4-07) takes
#: ``("src",)`` alone. The property is worded over the *core*: core resolves
#: the adapter a deployment names and names none of them itself. Every other
#: tree may legitimately name one — an example that boots a particular store
#: has to say which store, a per-backend test has to say which backend, and the
#: runtime's operational surfaces report back the name a deployment supplied.
#: A rule that fired there would be measuring the wrong thing. The rule's two
#: package-level exemptions live in ``tools/lints/substrate_names.py`` rather
#: than here, because they are about packages *inside* ``src``, not trees.
#:
#: ``no-hardcoding`` also covers ``archive`` (plan ``23-03``). **This mapping is
#: a POSITIVE scope** — read the paragraph above: rules absent from it inherit
#: every linted tree, but a rule PRESENT in it names its trees and inherits
#: nothing. So widening ``LINTED_TREES`` alone would have left CINV-01 skipping
#: the entire archive, silently, with the gate exiting 0. Archived example code
#: is still example code and CLAUDE.md §6.4 binds it to the No-Hardcoding Rule,
#: so the member belongs here as much as ``examples`` does.
#:
#: The other five rules take **no** archive entry, and that is a decision rather
#: than an omission: they are scoped ``("src", "runtime")`` and ``("src",)``,
#: which the archive was never a member of, so it is outside them by
#: construction. CINV-02 in particular must stay off the archive for the same
#: reason it stays off ``examples`` — CLAUDE.md §7.3 words the invariant over
#: core, and ``archive/examples/03-harness-portability`` necessarily imports
#: harness SDKs. ``tools/lints/tests/test_scope.py`` asserts the non-edit so a
#: later symmetry pass cannot quietly add one.
RULE_TREE_SCOPE: dict[str, tuple[str, ...]] = {
    "no-hardcoding": ("src", "runtime", "examples", "tests", "archive"),
    "harness-imports": ("src", "runtime"),
    "algorithmic": ("src", "runtime"),
    "orchestration-imports": ("src", "runtime"),
    "backend-imports": ("src", "runtime"),
    "substrate-names": ("src",),
}

#: Directories never worth walking.
SKIP_DIRS: frozenset[str] = frozenset(
    {"__pycache__", ".git", ".venv", "venv", "build", "dist", ".mypy_cache"}
)

Checker = Callable[[pathlib.Path, str], list[str]]
TreeChecker = Callable[[pathlib.Path], list[str]]

#: ``substrate_names.check`` carries an optional third ``base=`` keyword that
#: the other checkers do not. The positional pair this runner calls is
#: unchanged, so it registers like any other per-file checker; the keyword is
#: for tests that pin a synthetic adapter package, and production runs let the
#: checker recover the base from the path it is given.
CHECKERS: dict[str, Checker] = {
    "no-hardcoding": no_hardcoding.check,
    "harness-imports": harness_imports.check,
    "algorithmic": algorithmic.check,
    "orchestration-imports": orchestration_imports.check,
    "backend-imports": backend_imports.check,
    "substrate-names": substrate_names.check,
}

#: Checkers that take the repo root rather than one module. `citations` is
#: here because a cross-file citation is a claim about a file other than the
#: one it appears in, and because it reads prose — Markdown and YAML as well
#: as Python — so neither `LINTED_TREES` nor the per-file walk above fits it.
#: Its own tree scope and its own exemptions are config surfaces inside
#: `tools/lints/citations.py`, on the same principle as `RULE_TREE_SCOPE`:
#: what a check does not cover is stated, not left to path accident.
WHOLE_TREE_CHECKERS: dict[str, TreeChecker] = {
    "citations": citations.check_tree,
    "hash-transparent-key": hash_transparent_key.check_tree,
}


def module_name_for(path: pathlib.Path, root: pathlib.Path) -> str:
    """Dotted module name for `path` relative to the linted tree `root`.

    ``src/ccf/operators/traversal.py`` -> ``ccf.operators.traversal``;
    ``src/ccf/__init__.py`` -> ``ccf``.
    """
    parts = list(path.relative_to(root).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def iter_python_files(root: pathlib.Path) -> Iterator[pathlib.Path]:
    """Yield every `.py` file under `root`, skipping build/VCS noise."""
    for path in sorted(root.rglob("*.py")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def run(
    base: pathlib.Path,
    rules: Sequence[str],
    allowlist: no_hardcoding.Allowlist | None = None,
) -> list[str]:
    """Run `rules` over every linted tree under `base`; return the findings."""
    active = allowlist if allowlist is not None else no_hardcoding.load_allowlist()
    findings: list[str] = []
    per_file = [rule for rule in rules if rule in CHECKERS]

    for tree in LINTED_TREES:
        root = base / tree
        if not root.is_dir():
            continue
        for path in iter_python_files(root):
            module_name = module_name_for(path, root)
            for rule in per_file:
                if tree not in RULE_TREE_SCOPE.get(rule, LINTED_TREES):
                    continue
                found = CHECKERS[rule](path, module_name)
                if rule == "no-hardcoding":
                    found = no_hardcoding.apply_allowlist(found, active)
                findings.extend(found)

    for rule in rules:
        if rule in WHOLE_TREE_CHECKERS:
            findings.extend(WHOLE_TREE_CHECKERS[rule](base))

    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.lints",
        description=(
            "CCF invariant lints. Blocking by design (D-07): nonzero exit on any"
            " finding, and no report-only mode exists."
        ),
    )
    parser.add_argument("--all", action="store_true", help="run every checker")
    parser.add_argument(
        "--no-hardcoding",
        dest="selected",
        action="append_const",
        const="no-hardcoding",
        help="CINV-01 (CLAUDE.md §6.4)",
    )
    parser.add_argument(
        "--harness-imports",
        dest="selected",
        action="append_const",
        const="harness-imports",
        help="CINV-02 (CLAUDE.md §7.3)",
    )
    parser.add_argument(
        "--algorithmic",
        dest="selected",
        action="append_const",
        const="algorithmic",
        help="CINV-03 (CLAUDE.md §11)",
    )
    parser.add_argument(
        "--orchestration-imports",
        dest="selected",
        action="append_const",
        const="orchestration-imports",
        help="D-06 orchestration/adapters split (D-IMPL-60)",
    )
    parser.add_argument(
        "--backend-imports",
        dest="selected",
        action="append_const",
        const="backend-imports",
        help="CINV-02 adapter-import ban (D-IMPL-93 property (1))",
    )
    parser.add_argument(
        "--substrate-names",
        dest="selected",
        action="append_const",
        const="substrate-names",
        help="CINV-04 no substrate name in core (D-IMPL-93 property (2))",
    )
    parser.add_argument(
        "--citations",
        dest="selected",
        action="append_const",
        const="citations",
        help="cross-file citation drift (tools/lints/citations.py)",
    )
    parser.add_argument(
        "--hash-transparent-key",
        dest="selected",
        action="append_const",
        const="hash-transparent-key",
        help=(
            "CINV-06 every defaulted CCFContract field new since 13bd250"
            " declares ccf_hash_transparent (D-IMPL-243 amendments 1 and 2)"
        ),
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help=(
            "also print what the citation scan could NOT check. Additive"
            " only: it never changes the exit code or hides a finding."
        ),
    )
    parser.add_argument(
        "--base",
        type=pathlib.Path,
        default=pathlib.Path.cwd(),
        help="repo root to lint (default: cwd)",
    )
    return parser


def citation_coverage(base: pathlib.Path) -> list[str]:
    """Human-readable coverage lines for the citation scan (``--report``)."""
    scan = citations.scan_tree(base)
    return [
        f"citations: {scan.total} matched in {scan.scanned_files} files"
        f" ({scan.exempt_files} files exempt as dated records)",
        f"  checked and passing:   {scan.checked}",
        f"  findings:              {len(scan.findings)}",
        f"  explicitly historical: {scan.historical}",
        f"  UNCHECKED — no anchor: {scan.no_anchor}",
        f"  UNCHECKED — anchor not resolvable: {scan.unusable_anchor}",
        f"  UNCHECKED — path ambiguous:        {scan.ambiguous_path}",
        f"  UNCHECKED — path unresolvable:     {scan.unresolved_path}",
    ]


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    every = list(CHECKERS) + list(WHOLE_TREE_CHECKERS)
    rules = every if args.all or not args.selected else args.selected

    if args.report and "citations" in rules:
        for line in citation_coverage(args.base):
            print(line)

    findings = run(args.base, rules)
    for finding in findings:
        print(finding)

    if findings:
        print(
            f"\n{len(findings)} CCF invariant violation(s)."
            " Fix the code, or — for CINV-01 only — add a reviewed entry to"
            " tools/lints/allowlist.yaml.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
