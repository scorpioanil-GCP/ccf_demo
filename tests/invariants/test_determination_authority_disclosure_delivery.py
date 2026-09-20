"""The `D-IMPL-254` invariant is recorded as SDK architecture, and its four sabotages exist.

``24.6-11`` Task 2; criterion 27. The ruling of record is ``D-IMPL-254``, which
Dave elevated out of the Q1–Q28 rulings and stated in his own words
(``24.6-RULINGS.md`` §3):

    *"Internal truth, governing authority, and permitted disclosure are
    distinct concerns. The fabric preserves the governed truth of why a
    determination was reached; Policy determines what of that truth may cross
    the consumer boundary; the response shell expresses only the permitted
    disclosure. Decision Replay preserves sufficient governed evidence to
    reconstruct both the determination and the disclosure decision."*

    *"That gives us four distinct layers: Determination → Authority →
    Disclosure → Delivery."*

Criterion 27 asks for two things, and plan ``24.6-08`` shipped the first: the
invariant **recorded** in the module docstrings of the resolver, the refusal
envelope and the door, cited SDK-defined under CLAUDE.md §11 rather than as a
whitepaper commitment. This module is the second: the invariant **enforced by
construction**, which criterion 27 spells out as *"criteria 6, 10, 21 and 22
are its four sabotages and every one goes RED when its sabotage is applied"*.

What that enforcement can and cannot be, stated plainly
-------------------------------------------------------

A sabotage's RED is proven where the sabotage lives — inside the module that
owns the guard, against a scratch copy of the source it corrupts. This module
does not re-run those sabotages, and it would be worse if it did: a second copy
of a sabotage is a second thing to keep in step with the source it mutates.

What this module holds is the claim the four sabotages depend on and none of
them can make about itself: **that they exist in the tree, by exact name, in
the module the criterion assigns them to, and that pytest collects them.** A
sabotage named in a plan and absent from the tree enforces nothing (T-24.6-39),
and a sabotage present in a file pytest never collects enforces nothing either.
Both halves are asserted, from the tree, and each predicate is watched
reporting an absence before its emptiness is trusted.

The three docstrings are read by AST rather than by ``grep``, for plan
``24.6-09``'s reason: a module's own prose can trip a source-text claim, and
``ast.get_docstring`` reads the docstring and nothing else.

CLAUDE.md's invariant lists are not edited, and that is the criterion's own instruction
---------------------------------------------------------------------------------------

Criterion 27 ends *"CLAUDE.md's own invariant lists are NOT edited (a revision
for Dave to order; no contradiction measured, ``24.6-RESEARCH.md`` §M7)"*, and
``D-IMPL-254``'s own text leaves adding the invariant to those lists as a
revision for Dave. §M7's measurement, recorded here so the claim travels with
the gate rather than only in a planning file: CLAUDE.md §3.1's Phase D bullet,
§16's named-invariant list and §11 were read against ``D-IMPL-254`` (at lines
308 to 317, 1371 to 1375 and 994 to 1060 as the document stood at 24.6 — both
lists have moved since, which is why they are located below by anchor text and
never by line number), and **no contradiction was measured** — each listed
invariant is orthogonal to the four layers or reinforced by them. Nothing was
returned to Dave under amendment 3 (4). The one tension worth naming is not a
contradiction: *"three validation gates"* is stated as a count in both lists
while ``run_gates`` already carries more tokens, which is
``D-IMPL-237``/``D-IMPL-238``'s existing reading rather than ``D-IMPL-254``'s
doing.

What the gate on CLAUDE.md is, and what it was
----------------------------------------------

The gate is the two seven-member architectural-invariant lists — the §3.1
Phase D review bullet's parenthetical and the §16 named-invariant bullet's
parenthetical — held SEMANTICALLY. Each list is located by a unique anchor
(its bullet's lead-in prose up to the opening bracket, never its members),
its parenthetical is split on commas with whitespace collapsed, and the
resulting ordered roster is compared for equality with the seven spelled out
in ``INVARIANT_LISTS``. An invariant added, removed, duplicated or substituted
reds the check, and the message names which list and what moved; a re-wrap, a
whitespace change, or any edit outside the two parentheticals does not. Every
control below plants its edit on a copy of the text: CLAUDE.md is read once
and never written.

Until this repair the gate was a whole-file byte pin — ``git diff --quiet``
against the phase base ``1022ad59``, on CLAUDE.md as well as the whitepaper.
That pin was red from ``4683f245``, Phase 24.6's own close commit (+33 lines,
a new §9 subsection, touching neither list), because CLAUDE.md is Dave's
living charter (CLAUDE.md §2) and changes under ordinary governance. A
phase-scoped fence written as a standing invariant over such a document is a
defect in proof machinery, not evidence about the invariant. The rulings, in
order: ``D-IMPL-269`` (2) carried the red by id as ``24.8-C-03`` and refused
it as a permanent standing red — *"if the thing being pinned is legitimately
mutable project governance, a raw constant may be the wrong proof
mechanism"*; ``D-IMPL-270`` (2) ordered the claim NARROWED rather than
retired or wrapped in a fence-expiry framework — *"The narrowed assertion
should survive unrelated CLAUDE.md edits and fail only if the protected
invariant itself moves improperly"*; ``D-IMPL-271`` (4) narrowed it to the
two seven-member lists and named the failure mode in advance — *"detect
addition, removal, duplication, or substitution of an invariant, not
whitespace"*, a byte-pin in disguise being a defect rather than a near-miss —
and ``D-IMPL-271`` (5) ordered the whitepaper sibling narrowed equivalently.
``D-IMPL-269`` and ``D-IMPL-270`` are on ``main``; ``D-IMPL-271`` was ruled
on branch ``phase-24.9`` and its clauses (4) and (5) were recorded on
``main``'s ``docs/DECISIONS.md`` at the release-qualification repair package
so this module's authority is in shipped history. This module re-implements
that branch's roster check without its ``tools/proof`` helpers, which do not
exist on ``main``.

The whitepaper leg is deliberately NOT narrowed here. This repair is tests,
documentation and pins only, and the whitepaper byte pin against
``PHASE_BASE`` stays exactly as it was, with its scratch-repository control,
until ``D-IMPL-271`` (5) is carried out as its own change.
"""

from __future__ import annotations

import ast
import pathlib
import re
import subprocess
import sys
import textwrap
from collections.abc import Sequence
from typing import NamedTuple

import pytest

# --- what the invariant IS, and where it is recorded --------------------------

#: The four layers, as the arrow string plan ``24.6-08`` wrote into the three
#: docstrings. Spelled once here; every assertion below reads this.
ARROW = "Determination → Authority → Disclosure → Delivery"

#: The two citations the recording must carry beside the arrow. The first says
#: this is SDK-defined mechanism under CLAUDE.md §11 rather than a whitepaper
#: commitment (the whitepaper is deliberately not edited, ``D-IMPL-253`` Q28);
#: the second names the decision of record.
REQUIRED_CITATIONS = ("CLAUDE.md §11", "D-IMPL-254")

#: The repository root, resolved from this file rather than from a working
#: directory, so the gate reads the same tree however pytest was invoked.
ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The three modules criterion 27 names, in the order it names them: the
#: resolver, the refusal envelope, the door.
INVARIANT_MODULES: tuple[str, ...] = (
    "src/ccf/products/resolver.py",
    "src/ccf/products/refusal.py",
    "src/ccf/products/door.py",
)

#: The phase base the whitepaper leg diffs against. ``git diff --quiet``
#: against it is the whole of that leg's not-edited claim, and the commit is
#: named rather than described so a reader can resolve it. CLAUDE.md is no
#: longer measured against it — see the module docstring for why a raw
#: constant was the wrong proof mechanism for a living governance document.
PHASE_BASE = "1022ad59"

#: The one document that stays byte-untouched against the phase base: the
#: whitepaper, which is not edited at all in this phase (``D-IMPL-253`` Q28).
#: CLAUDE.md left this tuple when its pin was narrowed; its invariant lists
#: are guarded by ``INVARIANT_LISTS`` below, never by bytes.
UNEDITED = ("docs/CCF_Whitepaper_1-2.md",)


# --- the two invariant rosters, and how each is found -------------------------

#: The governance document the two rosters live in. Named, never pinned: what
#: this module protects is the rosters, not the file's bytes.
GOVERNANCE_DOCUMENT = "CLAUDE.md"


class InvariantList(NamedTuple):
    """One protected roster: where it is, and the seven it must be."""

    #: A human-readable name for the list, carried into every failure message
    #: so a red says WHICH list moved.
    list_id: str
    #: The bullet's lead-in prose up to and including the bracket that opens
    #: the list, unique in the document. Matched with whitespace runs
    #: collapsed, so the anchor survives a re-wrap — and deliberately NOT the
    #: list's first members, so an edit to any member, the first included, is
    #: reported as a roster change rather than as a lost anchor.
    anchor: str
    #: The seven members, in order, in this list's own wording.
    expected: tuple[str, ...]


#: The two seven-member architectural-invariant rosters.
#:
#: **The anchor is the contract; a line number is not.** Both lists have moved
#: since 24.6, and a line number would send this check at whatever text
#: happened to arrive at that offset. Each anchor is asserted to occur exactly
#: once before it is used, beside a sentinel that occurs zero times — a count
#: without its positive control is not a measurement.
#:
#: **The two lists are worded differently and that is deliberate.** §3.1's
#: Phase D review bullet says "single-writer", "audit-by-construction",
#: "No-Hardcoding"; §16's named-invariant list says "single-writer
#: enforcement", "audit-by-construction for HITL", "the No-Hardcoding Rule".
#: Each is held against its own seven and neither is normalized into the
#: other, because a normalization would hide a substitution in whichever
#: direction it ran.
INVARIANT_LISTS: tuple[InvariantList, ...] = (
    InvariantList(
        list_id="CLAUDE.md §3.1 Phase D review",
        anchor="the design preserves every named invariant (",
        expected=(
            "single-writer",
            "composition-preservation",
            "three validation gates",
            "Algorithmic ⇄ Semantic Alternation",
            "audit-by-construction",
            "No-Hardcoding",
            "zero harness imports in core",
        ),
    ),
    InvariantList(
        list_id="CLAUDE.md §16 named architectural invariants",
        anchor="listing every named architectural invariant (",
        expected=(
            "single-writer enforcement",
            "composition-preservation",
            "three validation gates",
            "Algorithmic ⇄ Semantic Alternation",
            "audit-by-construction for HITL",
            "the No-Hardcoding Rule",
            "zero harness imports in core",
        ),
    ),
)

#: Parametrization ids, ASCII so a node id stays typeable: pytest escapes the
#: ``§`` in the list ids above into ``\xa7`` and a reader could not paste the
#: result back into a ``pytest`` invocation.
ROSTER_IDS = ("section-3.1-phase-D-review", "section-16-named-invariants")

#: Appended to an anchor to build one that cannot match. An anchor count of
#: one means nothing until the same mechanism is watched reporting zero.
ABSENT_ANCHOR_SUFFIX = "ZZNOSUCH"

#: The unrelated prose the elsewhere control plants. Written to look like the
#: edits CLAUDE.md actually receives — a subsection heading, commas, a
#: parenthetical of its own, and a bare mention of an invariant's name
#: outside either list — none of which may move the rosters.
UNRELATED_PROSE = (
    "\n### A subsection Dave ordered, unrelated to the invariant lists\n\n"
    "Prose that mentions single-writer in passing (with, commas, and a\n"
    "parenthetical of its own) and changes nothing about which invariants\n"
    "the design must preserve.\n\n"
)


class InvariantListNotFound(AssertionError):
    """A roster's anchor does not occur exactly once, or never closes.

    Raised rather than skipped, so the check cannot pass vacuously when its
    subject disappears. Zero occurrences is a drifted anchor — re-anchor it;
    two or more is ambiguous, and would silently pin whichever came first.
    """

    def __init__(self, list_id: str, reason: str) -> None:
        self.list_id = list_id
        super().__init__(f"the {list_id} invariant list was not found: {reason}")


class InvariantRosterChanged(AssertionError):
    """A roster's members are not the seven pinned for that list.

    Carries what moved as attributes, so a control can assert on the addition
    or the removal by value rather than by parsing a message — and the
    message names WHICH list, because a red that does not say which list is
    weaker than the byte-pin it replaces.
    """

    def __init__(
        self, *, list_id: str, found: tuple[str, ...], expected: tuple[str, ...]
    ) -> None:
        self.list_id = list_id
        self.found = found
        self.expected = expected
        self.added = tuple(member for member in found if member not in expected)
        self.removed = tuple(member for member in expected if member not in found)
        self.duplicated = tuple(
            sorted({member for member in found if found.count(member) > 1})
        )
        self.reordered = (
            not self.added
            and not self.removed
            and not self.duplicated
            and sorted(found) == sorted(expected)
        )
        super().__init__(
            f"the {list_id} invariant roster is not the seven it has always been."
            f"\n  added:      {self.added}"
            f"\n  removed:    {self.removed}"
            f"\n  duplicated: {self.duplicated}"
            f"\n  reordered:  {self.reordered}"
            f"\n  found:      {found}"
            f"\n  expected:   {expected}"
            "\n An invariant entering or leaving this list is a governance change"
            " Dave orders, not one a phase makes in passing."
        )


def _anchor_pattern(anchor: str) -> re.Pattern[str]:
    """``anchor`` as a regex whose whitespace runs match any whitespace run.

    This is the first half of what makes the check semantic. Both anchors end
    at the bracket the list opens with, which in today's wrapping sits on the
    line after the lead-in, so a literal search would stop matching the
    moment that lead-in was re-wrapped — and a check that loses its subject
    to reflow is the byte-pin in disguise ``D-IMPL-271`` (4) named in advance.
    """
    return re.compile(r"\s+".join(re.escape(part) for part in anchor.split()))


def _parenthetical(document: str, invariant_list: InvariantList) -> str:
    """The bracketed span after the anchor, from the ``(`` it ends with to the matching ``)``.

    Bracket-matched rather than read to the next ``)``, so a nested
    parenthetical inside a roster would not truncate it.
    """
    matches = list(_anchor_pattern(invariant_list.anchor).finditer(document))
    if len(matches) != 1:
        raise InvariantListNotFound(
            invariant_list.list_id,
            f"its anchor {invariant_list.anchor!r} occurs {len(matches)} times,"
            " not exactly once — zero means the anchor has drifted and this"
            " check is reading nothing, two or more means it is ambiguous and"
            " would pin whichever came first",
        )
    # The anchor ends with the bracket that opens the list, so the span starts
    # on the anchor's last character.
    start = matches[0].end() - 1
    assert document[start] == "(", invariant_list.anchor
    depth = 0
    for index in range(start, len(document)):
        if document[index] == "(":
            depth += 1
        elif document[index] == ")":
            depth -= 1
            if depth == 0:
                return document[start : index + 1]
    raise InvariantListNotFound(
        invariant_list.list_id,
        f"it opens at its anchor {invariant_list.anchor!r} and never closes:"
        " no matching ')' before the end of the document",
    )


def invariant_members(document: str, invariant_list: InvariantList) -> tuple[str, ...]:
    """The members of one roster, in order, normalized.

    This is what makes the check SEMANTIC rather than a byte-pin in disguise.
    The parenthetical is split on commas and every member has its internal
    whitespace — newlines included — collapsed to single spaces, so the tuple
    is the same however the list is wrapped. Compared by equality against the
    pinned seven it detects **addition, removal, duplication and
    substitution** and is blind to reflow, which is exactly the property
    ``D-IMPL-271`` (4) requires. Order is kept: a permutation of the seven is
    still an edit inside the protected list, and it is reported as one.
    """
    inner = _parenthetical(document, invariant_list)[1:-1]
    return tuple(re.sub(r"\s+", " ", part).strip() for part in inner.split(","))


def assert_invariant_roster(document: str, invariant_list: InvariantList) -> None:
    """The claim: one roster is the seven pinned for it, in order.

    What moved is reported *beside* the tuples rather than instead of them: a
    count cannot see a swap, so the message has to name what changed and not
    merely how many there are.
    """
    found = invariant_members(document, invariant_list)
    if found != invariant_list.expected:
        raise InvariantRosterChanged(
            list_id=invariant_list.list_id,
            found=found,
            expected=invariant_list.expected,
        )


def _with_members(
    document: str, invariant_list: InvariantList, members: Sequence[str]
) -> str:
    """A copy of ``document`` whose roster is rewritten to ``members``.

    The single mutation primitive behind the removal, duplication and
    substitution controls. It rewrites the parenthetical on one line, which is
    itself a reflow the check must be blind to — so a red from one of those
    controls is a red about the membership and nothing else.
    """
    original = _parenthetical(document, invariant_list)
    return document.replace(original, "(" + ", ".join(members) + ")", 1)


# --- the four sabotages, by criterion ----------------------------------------

#: The roster criterion 27 names, one row per shipped sabotage function.
#:
#: Read the fourth column as *what its RED proves*, because that is what makes
#: this a roster of enforcement rather than a list of names:
#:
#: ===========  =========================================================
#: Criterion    What the sabotage's RED proves about ``D-IMPL-254``
#: ===========  =========================================================
#: 6            **Authority is a record, never a scalar.** A resolution that
#:              collapsed provenance to an effective number would still
#:              answer every question about the value and none about who set
#:              it — which is the first of the four mistakes Dave's text says
#:              the layering exists to prevent.
#: 10           **Naming a policy is not authority to override it.** An
#:              override honored on its name alone would put the Authority
#:              layer under the caller's control, so the layer would exist and
#:              decide nothing.
#: 21           **Disclosure withholds the internal cause.** The internal
#:              statement crossing at ``minimal`` is *"destroying audit truth
#:              to achieve suppression silence"* inverted: the truth survives
#:              and the silence does not.
#: 22           **Delivery expresses only the permitted disclosure.** Two
#:              subjects a policy says are indistinguishable becoming
#:              distinguishable at a door is the Delivery layer deciding
#:              something the Disclosure layer already decided.
#: ===========  =========================================================
#:
#: Each row is asserted present **by AST** in its module — never by ``grep``,
#: which would find a name in a comment — and asserted collected by pytest.
SABOTAGES: tuple[tuple[int, str, str], ...] = (
    (
        6,
        "tests/products/test_policy_constraints.py",
        "test_provenance_is_never_a_scalar_sabotage",
    ),
    (
        10,
        "tests/products/test_policy_constraint_resolver.py",
        "test_a_name_only_override_being_honored_is_red_sabotage",
    ),
    (
        21,
        "tests/products/test_disclosure.py",
        "test_leaking_the_internal_cause_at_minimal_is_red_sabotage",
    ),
    # Criterion 22 is a pair rather than a single function: the ruling is about
    # two subjects being indistinguishable AT A DOOR, and there are two doors.
    # Each is parametrized over the three disclosure levels, so the name below
    # is the function and the `minimal` leg is asserted separately by node id.
    (
        22,
        "tests/http_api/test_product_disclosure.py",
        "test_unauthorized_and_nonexistent_are_observationally_equivalent",
    ),
    (
        22,
        "tests/mcp/test_egress_disclosure.py",
        "test_unauthorized_and_nonexistent_are_observationally_equivalent",
    ),
)

#: The divergence controls beside criterion 22's two equivalence tests — the
#: functions that show the comparison **reporting** a planted divergence.
#:
#: They are rostered because an equivalence assertion is worth exactly as much
#: as the comparison behind it: a helper that returned no violations for
#: everything would make both equivalence tests green forever, and no sabotage
#: of the doors would ever go RED. Enumerated by name rather than counted, for
#: the reason a count over a roster stops naming its members.
EQUIVALENCE_CONTROLS: tuple[tuple[str, str], ...] = (
    (
        "tests/http_api/test_product_disclosure.py",
        "test_the_comparison_refuses_a_single_answer",
    ),
    (
        "tests/http_api/test_product_disclosure.py",
        "test_a_status_divergence_is_reported",
    ),
    (
        "tests/http_api/test_product_disclosure.py",
        "test_an_evidence_presence_divergence_is_reported",
    ),
    (
        "tests/http_api/test_product_disclosure.py",
        "test_a_field_set_divergence_is_reported",
    ),
    (
        "tests/http_api/test_product_disclosure.py",
        "test_a_sentinel_against_a_reference_is_reported",
    ),
    (
        "tests/http_api/test_product_disclosure.py",
        "test_a_reference_that_does_not_resolve_is_reported",
    ),
    (
        "tests/mcp/test_egress_disclosure.py",
        "test_the_comparison_refuses_a_single_answer",
    ),
    ("tests/mcp/test_egress_disclosure.py", "test_the_status_control_fires"),
    (
        "tests/mcp/test_egress_disclosure.py",
        "test_the_evidence_presence_control_fires",
    ),
    ("tests/mcp/test_egress_disclosure.py", "test_the_field_set_control_fires"),
    (
        "tests/mcp/test_egress_disclosure.py",
        "test_the_sentinel_versus_reference_control_fires",
    ),
)

#: The level criterion 22 names. Both equivalence tests are parametrized over
#: the three levels, so the leg the criterion is about is pinned by node id
#: rather than assumed to be among them.
CRITERION_22_LEVEL = "minimal"


# --- predicates over the tree -------------------------------------------------


def missing_from_docstring(source: str) -> list[str]:
    """What a module's docstring fails to say, of the three required things.

    A function over its subject, so the control below can hand it a corrupted
    copy and watch it report — rather than asserting an emptiness over the
    tree that has only ever been empty.

    Read by AST: a module whose *prose elsewhere* mentioned the arrow would
    satisfy a source-text search while recording nothing, and plan ``24.6-09``
    already had to move one claim off ``grep`` for exactly that reason.
    """
    docstring = ast.get_docstring(ast.parse(source)) or ""
    return [
        wanted
        for wanted in (ARROW, *REQUIRED_CITATIONS)
        if wanted not in docstring
    ]


def function_names(source: str) -> frozenset[str]:
    """Every module-level function defined in ``source``, by name.

    Module-level rather than any ``FunctionDef`` anywhere: a name that pytest
    collects is a name at module scope, so a helper nested inside another test
    must not satisfy the roster.
    """
    tree = ast.parse(source)
    return frozenset(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )


def _read(relative: str) -> str:
    path = ROOT / relative
    assert path.is_file(), f"{relative} is not in the tree"
    return path.read_text(encoding="utf-8")


def _collected_node_ids(modules: tuple[str, ...]) -> frozenset[str]:
    """Every node id pytest collects over ``modules``, as a set.

    A subprocess, because collection is what is being measured: the question
    is whether *pytest* reaches these functions, and asking the running
    session about another module's items would answer a different question.
    """
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "--no-header",
            "-p",
            "no:cacheprovider",
            *modules,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return frozenset(
        line.strip()
        for line in completed.stdout.splitlines()
        if "::" in line and not line.startswith(" ")
    )


@pytest.fixture(scope="module")
def governance_text() -> str:
    """CLAUDE.md, read once for every roster test and control in this module.

    Text in memory is the only thing the controls mutate. The last test in the
    module compares the file with this text again, so a control that wrote
    the document would be caught in the same run.
    """
    return _read(GOVERNANCE_DOCUMENT)


# --- (a) the invariant is recorded -------------------------------------------


@pytest.mark.parametrize("module", INVARIANT_MODULES)
def test_the_module_docstring_records_the_invariant(module: str) -> None:
    """Criterion 27's first half: the three docstrings say it, and cite it.

    The arrow alone is not the recording. A docstring naming the four layers
    without saying that they are SDK-defined under CLAUDE.md §11 would leave a
    reader to infer that the whitepaper committed to them, which is exactly the
    inference ``D-IMPL-253`` Q28 refuses — the whitepaper is not edited, and
    the extension is labeled as one.
    """
    assert missing_from_docstring(_read(module)) == [], (
        f"{module} does not record the invariant: "
        f"{missing_from_docstring(_read(module))}"
    )


def test_a_docstring_without_the_sentence_is_caught(tmp_path: pathlib.Path) -> None:
    """The control: the predicate is watched reporting, on a scratch copy.

    Three plants, one per required element, because a predicate that only ever
    looked for the arrow would pass a docstring that dropped both citations.
    The mutation is a copy under ``tmp_path``; the shipped module is read and
    never written, and the no-edit guard below measures that.
    """
    source = _read("src/ccf/products/door.py")
    docstring = ast.get_docstring(ast.parse(source)) or ""
    assert docstring, "the control needs a module that HAS a docstring"

    for removed in (ARROW, *REQUIRED_CITATIONS):
        assert docstring.count(removed) >= 1, removed
        scratch = tmp_path / f"door_without_{abs(hash(removed))}.py"
        scratch.write_text(source.replace(removed, "", 1), encoding="utf-8")
        assert removed in missing_from_docstring(
            scratch.read_text(encoding="utf-8")
        ), (
            f"a docstring with {removed!r} removed was not reported: the"
            " recording gate is measuring nothing"
        )

    # And the shipped source, through the same predicate, is clean — so the
    # green above is this predicate's and not an empty read's.
    assert missing_from_docstring(source) == []


# --- (b) the four sabotages exist, and pytest collects them -------------------


def test_the_roster_covers_the_four_criteria_the_invariant_names() -> None:
    """Criterion 27 names four criteria; the roster answers for all four.

    A roster, not a count (``verify-rosters-not-counts``): a roster of five
    rows one of which pointed at the wrong criterion would satisfy "five"
    forever. The set of criteria covered is compared for equality against the
    four the criterion names.
    """
    assert {criterion for criterion, _module, _name in SABOTAGES} == {6, 10, 21, 22}


@pytest.mark.parametrize(
    ("criterion", "module", "name"),
    SABOTAGES,
    ids=[f"c{criterion}-{name}" for criterion, _module, name in SABOTAGES],
)
def test_every_sabotage_in_the_roster_is_defined_in_its_module(
    criterion: int, module: str, name: str
) -> None:
    """T-24.6-39: a sabotage named in a plan and absent from the tree enforces nothing."""
    defined = function_names(_read(module))
    assert name in defined, (
        f"criterion {criterion}'s sabotage {name!r} is not defined at module"
        f" scope in {module}; the guard it is supposed to hold is unwatched"
    )


@pytest.mark.parametrize(
    ("module", "name"),
    EQUIVALENCE_CONTROLS,
    ids=[f"{pathlib.Path(m).stem}-{n}" for m, n in EQUIVALENCE_CONTROLS],
)
def test_every_equivalence_control_is_defined_in_its_module(
    module: str, name: str
) -> None:
    """Criterion 22's equivalence tests are only worth their comparison's controls."""
    assert name in function_names(_read(module)), (
        f"{name!r} is not defined at module scope in {module}; criterion 22's"
        " equivalence assertion at that door rests on a comparison nothing"
        " watches"
    )


def test_the_ast_presence_check_reports_an_absent_function() -> None:
    """The control for both roster checks above.

    Watched from both sides: a name the source defines is found, and a name it
    does not define is not. Without the second half, a predicate that returned
    every possible name would satisfy every row of the roster.
    """
    source = "def test_a(): pass\n\n\ndef helper(): pass\n"
    assert function_names(source) == frozenset({"test_a", "helper"})
    assert "test_b" not in function_names(source)

    # A function nested inside another is deliberately NOT reported: pytest
    # does not collect one, so a roster satisfied by one would be satisfied by
    # a sabotage that never runs.
    nested = "def test_a():\n    def test_inner(): pass\n"
    assert function_names(nested) == frozenset({"test_a"})


def test_every_rostered_function_is_collected_by_pytest() -> None:
    """The other half of existence: pytest reaches them.

    A sabotage defined in a file pytest never collects — a module outside the
    rootdir, a name a plugin deselects, a file whose import fails — enforces
    exactly as much as a sabotage that does not exist. So the roster is held
    against what pytest actually reports, and criterion 22's own level is
    pinned by node id, because both equivalence tests are parametrized over
    three levels and the criterion is about one of them.
    """
    modules = tuple(
        sorted({module for _criterion, module, _name in SABOTAGES})
        + sorted({module for module, _name in EQUIVALENCE_CONTROLS})
    )
    collected = _collected_node_ids(tuple(sorted(set(modules))))
    assert collected, "collection reported nothing — the roster proves nothing"

    for _criterion, module, name in SABOTAGES:
        prefix = f"{module}::{name}"
        assert any(node.startswith(prefix) for node in collected), prefix

    for module, name in EQUIVALENCE_CONTROLS:
        prefix = f"{module}::{name}"
        assert any(node.startswith(prefix) for node in collected), prefix

    for _criterion, module, name in SABOTAGES:
        if _criterion != 22:
            continue
        assert f"{module}::{name}[{CRITERION_22_LEVEL}]" in collected, (
            f"{module}::{name} is collected but not at {CRITERION_22_LEVEL!r},"
            " which is the level criterion 22 is about"
        )

    # The control on the collector itself: a name nothing defines is absent.
    assert not any(
        node.startswith("tests/products/test_disclosure.py::test_nothing_defines_this")
        for node in collected
    )


# --- (c) the invariant rosters CLAUDE.md carries ------------------------------


@pytest.mark.parametrize("invariant_list", INVARIANT_LISTS, ids=ROSTER_IDS)
def test_the_invariant_roster_is_the_seven_it_has_always_been(
    invariant_list: InvariantList, governance_text: str
) -> None:
    """The narrowed claim, on the real document: two rosters, not the file.

    What this replaces said of itself: *"A diff against the phase base says
    both, and says them about the whole file rather than about the lists —
    which is stronger and is what the criterion asks for."* Saying it about
    the whole file was not stronger; it was a phase-scoped fence written as a
    standing invariant over a document that changes under ordinary
    governance, and the phase that wrote it broke it in its own close commit.
    ``D-IMPL-271`` (4): *"The durable thing worth protecting is the invariant
    roster, not the entire governance document."* So the claim is narrowed to
    the durable thing — a correction rather than a weakening, because the old
    pin could not tell an invariant leaving the roster from a typo fixed in
    §9, and this one can.
    """
    assert_invariant_roster(governance_text, invariant_list)


@pytest.mark.parametrize("invariant_list", INVARIANT_LISTS, ids=ROSTER_IDS)
def test_the_anchor_occurs_exactly_once(
    invariant_list: InvariantList, governance_text: str
) -> None:
    """The anchor is asserted unique BEFORE it is used, with its sentinel.

    Two halves, and the second is the one that makes the first a measurement:
    the real anchor matches once, and the same mechanism handed an anchor
    nothing can match reports zero. A count with no positive control is a
    number, not evidence.
    """
    pattern = _anchor_pattern(invariant_list.anchor)
    assert len(pattern.findall(governance_text)) == 1, (
        f"{invariant_list.list_id}: {invariant_list.anchor!r} does not occur"
        f" exactly once in {GOVERNANCE_DOCUMENT}"
    )
    sentinel = invariant_list.anchor + ABSENT_ANCHOR_SUFFIX
    assert _anchor_pattern(sentinel).findall(governance_text) == [], (
        f"{sentinel!r} matched something: the anchor mechanism finds text that"
        " is not there, so the count above measures nothing"
    )
    assert len(invariant_list.expected) == 7, invariant_list.list_id


@pytest.mark.parametrize("invariant_list", INVARIANT_LISTS, ids=ROSTER_IDS)
def test_an_eighth_invariant_planted_in_the_list_is_caught(
    invariant_list: InvariantList, governance_text: str
) -> None:
    """Addition, watched — planted as a new wrapped line, named in the red.

    ``D-IMPL-254``'s four layers entering either roster is precisely the
    governance change criterion 27 leaves for Dave to order, so it is the
    right thing to plant. It is planted the way a real edit would land — a
    new line inside the wrapped parenthetical, before its closing bracket —
    rather than by rewriting the list, so the parser is exercised on the
    document's own wrapping plus one line.
    """
    original = _parenthetical(governance_text, invariant_list)
    planted = original[:-1] + f",\n  {ARROW})"
    copy = governance_text.replace(original, planted, 1)
    assert copy != governance_text, "the control planted nothing"

    with pytest.raises(InvariantRosterChanged) as raised:
        assert_invariant_roster(copy, invariant_list)
    assert raised.value.list_id == invariant_list.list_id
    assert raised.value.added == (ARROW,), raised.value.added
    assert raised.value.removed == ()
    assert ARROW in str(raised.value), str(raised.value)
    assert invariant_list.list_id in str(raised.value), str(raised.value)


@pytest.mark.parametrize("invariant_list", INVARIANT_LISTS, ids=ROSTER_IDS)
def test_a_removed_invariant_is_caught(
    invariant_list: InvariantList, governance_text: str
) -> None:
    """Removal, watched — every one of the seven, each named in its red.

    All seven rather than one, because a parser that happened to drop the
    first or the last member would pass a control that only removed one from
    the middle.
    """
    expected = invariant_list.expected
    for position, member in enumerate(expected):
        remaining = expected[:position] + expected[position + 1 :]
        copy = _with_members(governance_text, invariant_list, remaining)
        assert copy != governance_text, member

        with pytest.raises(InvariantRosterChanged) as raised:
            assert_invariant_roster(copy, invariant_list)
        assert raised.value.list_id == invariant_list.list_id
        assert raised.value.removed == (member,), raised.value.removed
        assert raised.value.added == (), raised.value.added
        assert member in str(raised.value), str(raised.value)


@pytest.mark.parametrize("invariant_list", INVARIANT_LISTS, ids=ROSTER_IDS)
def test_a_duplicated_invariant_is_caught(
    invariant_list: InvariantList, governance_text: str
) -> None:
    """Duplication, watched — a set comparison would miss this, a tuple does not.

    A duplicate adds nothing to the set and removes nothing from it, which is
    why the exception reports it as its own kind of change rather than
    leaving it to fall out of the added/removed lines as an empty pair.
    """
    expected = invariant_list.expected
    for position, member in enumerate(expected):
        doubled = expected[: position + 1] + (member,) + expected[position + 1 :]
        copy = _with_members(governance_text, invariant_list, doubled)
        assert copy != governance_text, member

        with pytest.raises(InvariantRosterChanged) as raised:
            assert_invariant_roster(copy, invariant_list)
        assert raised.value.list_id == invariant_list.list_id
        assert raised.value.duplicated == (member,), raised.value.duplicated
        assert raised.value.added == ()
        assert raised.value.removed == ()
        assert member in str(raised.value), str(raised.value)


@pytest.mark.parametrize("invariant_list", INVARIANT_LISTS, ids=ROSTER_IDS)
def test_a_substituted_invariant_is_caught(
    invariant_list: InvariantList, governance_text: str
) -> None:
    """Substitution, watched — the count stays seven and the red still names both.

    A floor on the roster's length would pass this edit: seven in, seven out.
    The red has to name the member that left AND the one that took its place,
    because a message naming only one of them leaves a reader to guess the
    other.
    """
    expected = invariant_list.expected
    for position, member in enumerate(expected):
        swapped = expected[:position] + (ARROW,) + expected[position + 1 :]
        assert len(swapped) == 7
        copy = _with_members(governance_text, invariant_list, swapped)
        assert copy != governance_text, member

        with pytest.raises(InvariantRosterChanged) as raised:
            assert_invariant_roster(copy, invariant_list)
        assert raised.value.list_id == invariant_list.list_id
        assert raised.value.added == (ARROW,), raised.value.added
        assert raised.value.removed == (member,), raised.value.removed
        assert member in str(raised.value) and ARROW in str(raised.value)


@pytest.mark.parametrize("invariant_list", INVARIANT_LISTS, ids=ROSTER_IDS)
def test_whitespace_and_rewrapping_leave_the_roster_green(
    invariant_list: InvariantList, governance_text: str
) -> None:
    """The byte-pin-in-disguise control, and it must be GREEN.

    ``D-IMPL-271`` (4) named this failure mode in advance — *"harmless
    formatting changes"* must not *"become another byte-pin in disguise"* —
    so its absence is proven here rather than promised.

    Five reflows, each one a real formatting edit CLAUDE.md could receive:
    the parenthetical joined onto one line; one member per line; every gap
    after a comma turned into a tab; a NARROW re-wrap at width 28; and the
    whitespace between the bullet's lead-in and the opening bracket flipped
    (a line break where there is a space, a space where there is a break).
    The narrow one is the control that matters most: wrapping at one member per
    line is reflow that ``str.strip`` alone survives, so at width 28 the line
    breaks are made to fall INSIDE members, which is the case the whitespace
    collapse exists for — and it is also how CLAUDE.md is really wrapped
    today (§16 carries "three" and "validation gates" on different lines).

    The wrap is at word boundaries only — ``break_on_hyphens=False``.
    Splitting ``single-writer`` across two lines is not a formatting change:
    it changes what the document renders, so refusing it is right rather
    than lenient.
    """
    original = _parenthetical(governance_text, invariant_list)
    one_line = re.sub(r"\s+", " ", original)
    one_per_line = "(" + ",\n  ".join(invariant_list.expected) + ")"
    tabbed = re.sub(r",\s*", ",\t", original)
    narrow = textwrap.fill(
        one_line,
        width=28,
        subsequent_indent="    ",
        break_on_hyphens=False,
        break_long_words=False,
    )
    assert any(
        "\n" in member.strip() for member in narrow[1:-1].split(",")
    ), (
        "no line break falls inside a member, so the narrow reflow is one a"
        " parser that only stripped its members would also survive — the"
        " control would not be measuring the whitespace collapse it exists for"
    )

    for label, reflowed in (
        ("one line", one_line),
        ("one member per line", one_per_line),
        ("tabs after commas", tabbed),
        ("narrow re-wrap", narrow),
    ):
        assert reflowed != original, f"the {label} control reflowed nothing"
        copy = governance_text.replace(original, reflowed, 1)
        assert copy != governance_text, label
        # No exception: the roster is the same seven however it is laid out.
        assert_invariant_roster(copy, invariant_list)
        assert invariant_members(copy, invariant_list) == invariant_list.expected

    # The fifth reflow moves the lead-in rather than the list: the anchor has
    # to survive its own re-wrap, or the check would lose the list to an edit
    # outside the parentheses.
    lead_in = _anchor_pattern(invariant_list.anchor).search(governance_text)
    assert lead_in is not None, invariant_list.anchor
    gap = " " if "\n" in lead_in.group(0) else "\n  "
    rewrapped_lead_in = (
        governance_text[: lead_in.start()]
        + re.sub(r"\s+", gap, lead_in.group(0))
        + governance_text[lead_in.end() :]
    )
    assert rewrapped_lead_in != governance_text, "the lead-in control reflowed nothing"
    assert_invariant_roster(rewrapped_lead_in, invariant_list)


def test_unrelated_prose_elsewhere_in_the_document_leaves_the_roster_green(
    governance_text: str,
) -> None:
    """The edit class that broke the old pin, planted four ways, and GREEN.

    ``4683f245`` added a whole §9 subsection and touched neither list; the
    old byte pin went red on it, and ``D-IMPL-271`` (4) rules that *"Ordinary
    edits — including the future §9 cleanup — must not red this proof."* The
    same class of edit is planted here at four places found structurally
    rather than by prose: the top of the document, the end of it, the
    paragraph immediately after the §16 list, and the next top-level section
    boundary after the §3.1 list. The planted prose deliberately carries a
    parenthetical with commas and a bare mention of an invariant's name, so
    neither of those can be what keeps this green.
    """
    section_31, section_16 = INVARIANT_LISTS
    after_16 = governance_text.index(
        "\n\n",
        governance_text.index(_parenthetical(governance_text, section_16)),
    )
    next_heading_after_31 = governance_text.index(
        "\n## ",
        governance_text.index(_parenthetical(governance_text, section_31)),
    )
    plants = (
        ("top of the document", 0),
        ("end of the document", len(governance_text)),
        ("paragraph after the §16 list", after_16),
        ("next top-level section after the §3.1 list", next_heading_after_31),
    )
    for label, offset in plants:
        copy = governance_text[:offset] + UNRELATED_PROSE + governance_text[offset:]
        assert copy != governance_text, label
        assert copy.count("\n") > governance_text.count("\n"), label
        for invariant_list in INVARIANT_LISTS:
            # No exception, and the anchor is still unique: the plant neither
            # moved a roster nor created a second copy of one.
            assert_invariant_roster(copy, invariant_list)
            assert len(_anchor_pattern(invariant_list.anchor).findall(copy)) == 1


@pytest.mark.parametrize("invariant_list", INVARIANT_LISTS, ids=ROSTER_IDS)
def test_a_missing_or_ambiguous_list_is_a_red_never_a_pass(
    invariant_list: InvariantList, governance_text: str
) -> None:
    """The vacuity control: the subject disappearing is a RED, never a pass.

    A check that quietly finds nothing to check is the failure CLAUDE.md §3.1
    names as collapsing *don't know* into *pass*. Two copies: one with the
    parenthetical deleted (the anchor loses its bracket: zero matches) and
    one with the lead-in and the list appended at the end of the document
    (two matches). Both must raise as list-not-found, naming the list, rather
    than return.
    """
    original = _parenthetical(governance_text, invariant_list)
    deleted = governance_text.replace(original, "", 1)
    doubled = governance_text + "\n" + invariant_list.anchor + original[1:] + "\n"
    for label, copy in (("deleted", deleted), ("doubled", doubled)):
        assert copy != governance_text, label
        with pytest.raises(InvariantListNotFound) as raised:
            assert_invariant_roster(copy, invariant_list)
        assert raised.value.list_id == invariant_list.list_id, label
        assert "not exactly once" in str(raised.value), str(raised.value)


# --- (d) the whitepaper is not edited ----------------------------------------


@pytest.mark.parametrize("document", UNEDITED)
def test_the_document_is_unchanged_since_the_phase_base(document: str) -> None:
    """``D-IMPL-253`` Q28, as a diff: the whitepaper is not edited at all.

    The whole-file pin is right for this document and was wrong for
    CLAUDE.md, and the difference is lifetime: the whitepaper is the canonical
    specification (CLAUDE.md §2) and does not change under ordinary
    governance, so a diff against the phase base is a standing claim about
    it. CLAUDE.md left this parametrization when its pin was narrowed to the
    two invariant rosters in section (c) above. ``D-IMPL-271`` (5) orders
    this sibling narrowed equivalently; that is a separate change, and the
    pin here is unchanged.
    """
    completed = subprocess.run(
        ["git", "diff", "--quiet", PHASE_BASE, "--", document],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, (
        f"{document} differs from {PHASE_BASE}: criterion 27 leaves it to Dave"
        f" to order a revision.\n{completed.stdout}{completed.stderr}"
    )


def test_the_unchanged_check_can_report_a_difference(tmp_path: pathlib.Path) -> None:
    """The control: ``git diff --quiet`` is shown answering non-zero.

    The subject is a scratch repository rather than this one, so nothing is
    written anywhere near the document the test above guards — and the
    predicate is still the same command with the same flags.
    """
    scratch = tmp_path / "scratch-repo"
    scratch.mkdir()

    def run(*argv: str) -> None:
        subprocess.run(
            argv, cwd=scratch, capture_output=True, text=True, check=True
        )

    run("git", "init", "-q")
    run("git", "config", "user.email", "fixture@example.invalid")
    run("git", "config", "user.name", "fixture")
    document = scratch / "DOCUMENT.md"
    document.write_text("the original\n", encoding="utf-8")
    run("git", "add", "DOCUMENT.md")
    run("git", "commit", "-q", "-m", "base")
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=scratch,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    unchanged = subprocess.run(
        ["git", "diff", "--quiet", base, "--", "DOCUMENT.md"],
        cwd=scratch,
        capture_output=True,
        text=True,
        check=False,
    )
    assert unchanged.returncode == 0

    document.write_text("the original, edited\n", encoding="utf-8")
    changed = subprocess.run(
        ["git", "diff", "--quiet", base, "--", "DOCUMENT.md"],
        cwd=scratch,
        capture_output=True,
        text=True,
        check=False,
    )
    assert changed.returncode != 0, (
        "git diff --quiet reported no difference over an edited file: the"
        " not-edited gate above is measuring nothing"
    )


def test_no_control_here_edits_the_real_source_tree(governance_text: str) -> None:
    """Every mutation above is a copy — under ``tmp_path`` or in memory.

    Asserted rather than assumed, because two controls write files (the
    docstring plant and the scratch repository) and the roster controls
    mutate text, and a plant that landed on the shipped path would be a
    sabotage nobody restored. The governance document is compared with the
    text the module-scoped fixture read at its first use — a measurement when
    this test runs after the controls, as it does in file order, and a
    trivial equality when it runs alone.
    """
    for module in (*INVARIANT_MODULES, *{m for _c, m, _n in SABOTAGES}):
        assert (ROOT / module).is_file(), module
    assert missing_from_docstring(_read("src/ccf/products/door.py")) == []
    assert _read(GOVERNANCE_DOCUMENT) == governance_text, (
        f"{GOVERNANCE_DOCUMENT} changed while this module's controls were"
        " running: a control wrote the document it was supposed to copy"
    )
    completed = subprocess.run(
        ["git", "status", "--porcelain", "--", "src", "runtime"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert completed.stdout.strip() == "", (
        "src/ or runtime/ is dirty while this module's controls were running:"
        f"\n{completed.stdout}"
    )
