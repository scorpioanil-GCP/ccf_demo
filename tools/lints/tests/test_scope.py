"""Tree-scope membership for the lint runner — the S-16 guard (plan 23-03).

Why membership and not a count
------------------------------

Every other non-vacuity gate in this tree is a **floor**: a count that says a
scan found at least N things. A floor cannot see a *swap*. Widening a scan root
to ``("src", "runtime", "archive", "tests")`` — dropping ``examples`` while
adding ``archive`` — leaves every count identical and every floor green while
the live examples tree silently stops being linted. ``23-RESEARCH.md`` finding
**S-16** names this: *"a floor cannot see a swap. Assert root membership, not
just the total."*

So the assertions here are on **membership**, and on exact set membership
rather than on ``in`` checks alone. An ``in`` check passes over a tuple that has
*grown*, and for a lint tree growth is the safe direction — but growth is also
how a tree quietly joins a scope nobody reviewed, and the message from a set
comparison names the member that moved.

What is asserted, and what deliberately is not
----------------------------------------------

``tools/lints/__main__.py::LINTED_TREES`` and
``tools/lints/__main__.py::RULE_TREE_SCOPE`` are separate assertions, because
they are separate mechanisms and the second is the one that matters.
``RULE_TREE_SCOPE`` is a **positive** per-rule scope — its own docstring says
*"Rules absent from this mapping run over every linted tree"* — and
``no-hardcoding`` is present in it, naming its trees explicitly. Adding a tree
to ``LINTED_TREES`` alone therefore does **not** put that tree under CINV-01;
the rule would skip it with the gate exiting 0. CLAUDE.md §6.4 binds example
code to the No-Hardcoding Rule, and the archive is still example code, so a
one-sided widening would take 265 archived files out of CINV-01's reach with
every check green.

The import rules are asserted in the opposite direction:
``harness-imports``, ``algorithmic``, ``orchestration-imports`` and
``backend-imports`` are scoped ``("src", "runtime")`` and ``substrate-names``
to ``("src",)``, so the archive is already outside all five *by construction* —
no scope entry was added for them, and this module asserts that non-edit so a
later "consistency" pass cannot add one without turning a test red. CLAUDE.md
§7.3 words CINV-02 over **core**, and ``archive/examples/03-harness-portability``
necessarily imports harness SDKs, exactly as ``examples/`` does today.

The runner-level proof that the config does what it says lives beside the
existing examples-scope tests in ``tests/lints/test_examples_scope.py``, which
drives ``tools/lints/__main__.py::run`` over synthetic trees. This module gates
the constants; that one gates the behaviour.
"""

from __future__ import annotations

from tools.lints.__main__ import LINTED_TREES, RULE_TREE_SCOPE
from tools.lints.citations import GATED_TREES

#: The live examples tree and the archive it is being retired into, named
#: together because the failure this module exists to catch is one being
#: swapped for the other.
LIVE_EXAMPLES_TREE = "examples"
ARCHIVE_TREE = "archive"

#: The trees the per-file lint walk covers, as a set. `D-03` pins the archive
#: root at `archive/examples/`; the tree name here is the top-level `archive`
#: deliberately — see `test_the_archive_member_is_the_inheriting_spelling`.
EXPECTED_LINTED_TREES = {"src", "runtime", "examples", "tests", "archive"}

#: The trees CINV-01 (No-Hardcoding) covers. Same membership as the walk today,
#: stated separately because they are separate mechanisms.
EXPECTED_NO_HARDCODING_TREES = {"src", "runtime", "examples", "tests", "archive"}

#: The rules whose scope must NOT reach the archive, each with why.
CORE_SCOPED_RULES: dict[str, str] = {
    "harness-imports": (
        "CLAUDE.md §7.3 words CINV-02 over core, and the archived harness"
        " portability example necessarily imports harness SDKs"
    ),
    "algorithmic": (
        "the Algorithmic/Semantic alternation is an invariant over the fabric,"
        " not over teaching material"
    ),
    "orchestration-imports": ("the orchestration split is a core-only property"),
    "backend-imports": (
        "an example that boots a particular store has to say which store"
    ),
    "substrate-names": ("CINV-04 is worded over the core alone"),
}


# --- LINTED_TREES ------------------------------------------------------------


def test_the_linted_trees_have_exactly_the_expected_membership() -> None:
    """Set equality, so a swap and a silent addition both fail with a name."""
    assert set(LINTED_TREES) == EXPECTED_LINTED_TREES, (
        "the lint walk's tree set changed. A tree ADDED here starts being"
        " linted without review; a tree REMOVED stops being linted with every"
        " count gate still green, because no floor in this tree can see a"
        " swap (23-RESEARCH.md S-16)."
    )


def test_both_the_live_examples_tree_and_the_archive_are_linted() -> None:
    """The swap S-16 describes, named member by member.

    Stated in addition to the set comparison above because this is the pair the
    archive move puts at risk, and a failure here says *which* of the two went
    missing rather than printing a set difference.
    """
    assert LIVE_EXAMPLES_TREE in LINTED_TREES, (
        "the live examples tree left the lint walk. CLAUDE.md §6.4 applies the"
        " No-Hardcoding Rule to /examples explicitly."
    )
    assert ARCHIVE_TREE in LINTED_TREES, (
        "the archive left the lint walk. `python -m tools.lints --all` was"
        " measured EXITING 0 over the moved trees before this member existed —"
        " a gate reporting clean because it stopped looking."
    )


def test_the_archive_member_is_the_inheriting_spelling() -> None:
    """`archive`, not `archive/examples` — and the asymmetry is deliberate.

    ``23-RESEARCH.md`` §14.9 flags the choice between the top-level tree name
    and the narrow path prefix as unsettled, noting the two differ in what a
    FUTURE archive sibling inherits. The two constants in this phase resolve it
    in **opposite** directions, on purpose:

    * This is a **lint**, and its default is default-allow: a future
      ``archive/anything`` should be linted the day it appears, without anyone
      remembering to widen a tuple. The inheriting spelling is the safe one.
    * ``tools/publish_scan.py::INCLUDE_ALLOWED_PREFIXES`` (plan 23-02,
      criterion 17) is a **publication** boundary and default-deny, so it took
      the NARROW spelling ``archive/examples/``. There, inheritance is the
      unsafe direction: ``archive/`` would admit every future sibling under the
      archive root to the published tree without anyone approving it.

    Both spellings are recorded at their own constant. This test exists so the
    asymmetry cannot be "corrected" into consistency without reading why.
    """
    assert ARCHIVE_TREE in LINTED_TREES
    assert "archive/examples" not in LINTED_TREES, (
        "LINTED_TREES holds top-level tree names, not path prefixes:"
        " `tools/lints/__main__.py::run` joins each member to the repo base and"
        " derives module names relative to it."
    )


# --- RULE_TREE_SCOPE ---------------------------------------------------------


def test_cinv01_scope_has_exactly_the_expected_membership() -> None:
    """The edit that actually puts the archive under CINV-01.

    ``RULE_TREE_SCOPE`` is a POSITIVE per-rule scope. ``no-hardcoding`` names
    its trees, so it does not inherit ``LINTED_TREES`` — widening the walk
    alone leaves this rule skipping the archive entirely.
    """
    assert set(RULE_TREE_SCOPE["no-hardcoding"]) == EXPECTED_NO_HARDCODING_TREES, (
        "CINV-01's tree scope changed. This is the mapping that decides whether"
        " the No-Hardcoding Rule reads a tree at all; LINTED_TREES membership"
        " does not imply it."
    )


def test_both_the_live_examples_tree_and_the_archive_are_under_cinv01() -> None:
    """The S-16 swap again, one mechanism further in."""
    assert LIVE_EXAMPLES_TREE in RULE_TREE_SCOPE["no-hardcoding"]
    assert ARCHIVE_TREE in RULE_TREE_SCOPE["no-hardcoding"], (
        "the archive is outside CINV-01's scope. Archived example code is still"
        " example code (CLAUDE.md §6.4) and a prompt literal there would go"
        " unreported with `python -m tools.lints --all` exiting 0."
    )


def test_no_core_scoped_rule_reaches_the_archive() -> None:
    """The non-edit, asserted so nobody adds one for symmetry's sake.

    These five rules already exclude the archive *by construction* — their
    scopes are ``("src", "runtime")`` and ``("src",)``, which the archive was
    never a member of. No scope entry was added for them in plan 23-03, and
    that finding is recorded here rather than in prose alone.
    """
    for rule, reason in CORE_SCOPED_RULES.items():
        assert ARCHIVE_TREE not in RULE_TREE_SCOPE[rule], f"{rule}: {reason}"
        assert LIVE_EXAMPLES_TREE not in RULE_TREE_SCOPE[rule], (
            f"{rule} gained the examples tree; the archive follows the same"
            f" posture and both would start firing. {reason}"
        )


def test_every_scoped_rule_names_only_trees_the_walk_visits() -> None:
    """A scope entry naming a tree outside the walk is a scope that does nothing.

    ``run`` iterates ``LINTED_TREES`` and consults ``RULE_TREE_SCOPE`` per tree,
    so a member here that is not in the walk is unreachable — the quietest way
    a rule's stated coverage stops matching its real coverage.
    """
    for rule, trees in RULE_TREE_SCOPE.items():
        unreachable = sorted(set(trees) - set(LINTED_TREES))
        assert not unreachable, (
            f"{rule} is scoped to {unreachable}, which the lint walk never"
            " visits; the scope claims coverage the runner cannot deliver."
        )


# --- GATED_TREES (the citation walk) -----------------------------------------


def test_the_citation_walk_reaches_both_the_examples_tree_and_the_archive() -> None:
    """The citation gate's own tree list, same S-16 reasoning.

    ``tools/lints/citations.py::GATED_TREES`` feeds
    ``tests/invariants/test_citation_coverage.py::MINIMUM_SCANNED_CITATION_HOSTS``,
    which is a floor — and a floor cannot see a swap either. Measured on this
    tree, 252 of the citation hosts the walk reads live in the ten condemned
    example trees; without the archive member the walk loses every one of them
    after the move.
    """
    assert LIVE_EXAMPLES_TREE in GATED_TREES
    assert ARCHIVE_TREE in GATED_TREES, (
        "the citation walk stops at the archive boundary; every citation in an"
        " archived file becomes unread, and the host floor goes red for a"
        " reason that reads like a legitimate removal."
    )


def test_the_gated_trees_have_exactly_the_expected_membership() -> None:
    """Set equality. The tuple was measured before it was written; keep it so."""
    assert set(GATED_TREES) == {
        "src",
        "runtime",
        "tools",
        "tests",
        "examples",
        "public",
        "docs",
        "perf",
        ".planning",
        ".github",
        "archive",
    }, (
        "the citation walk's tree set changed. Its own comment records that"
        " every top-level tracked directory was scanned for citations before"
        " the tuple was written, and that the two absent from it carry none —"
        " so an addition or a removal here is a claim about the tree that"
        " somebody has to have measured."
    )
