"""The assembler may not silently swallow a fragment line.

``tools/assemble_surface_changes.py`` had been **dropping the first line of any
bare bullet inside a field block and joining the rest onto the previous field**.
:func:`tools.assemble_surface_changes._collect_fields` carries the mechanism and
the measurement; this module is the door that makes it a red build.

Why the branch needed a door of its own
---------------------------------------

The refusal lives in the assembler's ``--check`` mode, and **nothing in this
repository invokes ``--check``**: ``Makefile``'s ``surface-changes`` target runs
write mode, and ``tests/test_surface_drift.py`` imports :func:`serialize`
directly. A refusal reachable only through an uninvoked flag is the
``D-IMPL-324`` pattern — *declaration is not a door* — so the strict read is
asserted here, in a suite ``make gate-tools`` and ``.github/workflows/ci.yml``
both run, over the fragments that actually ship.

What each test proves, and what it would take to make it lie
------------------------------------------------------------

:func:`test_no_shipped_fragment_carries_a_line_the_assembler_would_swallow` is
the ratchet: it reads the live ``docs/surface-changes/`` tree strictly, so a
fragment added later with a bare bullet reddens here rather than publishing a
sentence fragment. It is paired with a **positive control** — a synthetic
fragment written into a temporary directory and read through the same parser —
because a ratchet over a walk that read nothing passes forever, which is the
posture ``tools/publish_scan.py::require_populated`` refuses.

The control is deliberately a *pair*: the same entry is read once with the bare
bullet (refused) and once with that one line indented by two spaces (accepted,
and the text present in the parsed block). A refusal test on its own cannot
distinguish a gate that refuses the defect from a gate that refuses everything.
"""

from __future__ import annotations

import pathlib

import pytest

from tools.assemble_surface_changes import (
    FIELDS,
    FragmentError,
    _collect_fields,
    fragment_paths,
    parse_entries,
)

#: The measured size of the population the strict read walks, as a floor. A
#: strict read over an empty fragment set reports clean and says nothing.
#: Measured 2026-09-26 on the wave-1 join: 175 fragments, 1,747 entries.
MINIMUM_FRAGMENTS = 170
MINIMUM_ENTRIES = 1700

#: The defect's own shape, as a fragment. ``- **Known limit:** …`` does not
#: match the assembler's field-bullet pattern (``[A-Z][A-Za-z ]*:`` admits no
#: ``*``), so it is neither a field nor a continuation, and the two indented
#: lines beneath it used to be joined onto ``Why``.
_BARE_BULLET_FRAGMENT = """# A synthetic fragment

## ccf.example.surface

- Surface: ccf.example.surface
- Public surface: false
- Change type: behavior
- Before: the swallowed line reached neither the fields nor the block
- After: it is refused by name
- Why: the published note lost its first clause
- Migration: none
- **Known limit, stated rather than closed:** this line is the one the
  assembler dropped, and these two indented lines were glued onto `Migration`
  rather than onto it
"""

#: The same entry with that one line indented by two spaces — a nested bullet,
#: which the assembler both keeps and publishes.
_CORRECTED_FRAGMENT = _BARE_BULLET_FRAGMENT.replace(
    "\n- **Known limit", "\n  - **Known limit"
)

_SWALLOWED_TEXT = "**Known limit, stated rather than closed:**"


def _entry_body(fragment: str) -> list[str]:
    """The ``## `` section's body lines, the way the assembler splits them."""
    from tools.assemble_surface_changes import _split_sections

    sections = _split_sections(fragment)
    assert len(sections) == 1, (
        "the synthetic fragment is supposed to carry exactly one section;"
        f" _split_sections found {len(sections)}"
    )
    return sections[0][1]


def test_the_strict_read_walks_the_shipped_fragments() -> None:
    """Non-vacuity. A ratchet over an empty walk passes forever."""
    fragments = fragment_paths()
    assert len(fragments) >= MINIMUM_FRAGMENTS, (
        f"the strict read walked {len(fragments)} fragments,"
        f" {MINIMUM_FRAGMENTS} expected. If fragments were legitimately"
        " removed, lower this constant in the same commit and name the removal"
        " in the commit message — do not leave a ceiling over a walk that read"
        " nothing."
    )
    entries = parse_entries(strict=True)
    assert len(entries) >= MINIMUM_ENTRIES, (
        f"the strict read parsed {len(entries)} entries,"
        f" {MINIMUM_ENTRIES} expected. A walk that reads files and finds no"
        " entries in any of them satisfies the file floor and still tells the"
        " refusal nothing."
    )


def test_no_shipped_fragment_carries_a_line_the_assembler_would_swallow() -> None:
    """The ratchet. Every fragment under ``docs/surface-changes/``, strictly."""
    try:
        parse_entries(strict=True)
    except FragmentError as refused:  # pragma: no cover - the failure path
        pytest.fail(
            "a fragment carries a line tools/assemble_surface_changes.py would"
            " DROP, publishing docs/SURFACE-CHANGES.md — the adopter-facing"
            " migration record — with an instruction missing its first clause."
            " The assembler's refusal, verbatim:\n\n"
            f"{refused}"
        )


def test_the_check_mode_refuses_a_bare_bullet_inside_a_field_block() -> None:
    """The positive control's refusing half, over the defect's own shape."""
    with pytest.raises(FragmentError) as refused:
        _collect_fields(
            _entry_body(_BARE_BULLET_FRAGMENT), "synthetic", strict=True
        )

    message = str(refused.value)
    assert "Migration" in message, (
        "the refusal must name the field whose value the swallowed line would"
        f" have been glued onto, so the author can see the damage: {message}"
    )
    assert _SWALLOWED_TEXT in message, (
        "the refusal must quote the offending line verbatim — the assembler"
        " cannot report its line number, so the quoted text is what makes it"
        f" greppable: {message}"
    )


def test_the_check_mode_accepts_the_same_line_indented() -> None:
    """The positive control's accepting half. Two spaces is the whole repair."""
    fields, block = _collect_fields(
        _entry_body(_CORRECTED_FRAGMENT), "synthetic", strict=True
    )

    assert set(FIELDS) <= set(fields), (
        "the corrected fragment must still parse as a complete seven-field"
        f" entry; got {sorted(fields)}"
    )
    assert any(_SWALLOWED_TEXT in line for line in block), (
        "the indented line must reach the verbatim block — the block is what"
        " the assembled document re-emits, so a line absent from it is a line"
        " absent from the published migration note"
    )
    assert _SWALLOWED_TEXT in fields["Migration"], (
        "as a nested bullet the line joins the open field's value, which is"
        " how it becomes visible rather than dropped"
    )


def test_the_permissive_read_still_swallows_it() -> None:
    """The defect, pinned. ``strict=False`` is unchanged behavior on purpose.

    The default has to stay permissive: ``tests/test_surface_completeness.py``
    and ``tests/test_surface_drift.py`` read the log through the same parser and
    were not asked to change. Pinning the swallow here means a later attempt to
    "fix" the default silently — which would move the drift gate's expected
    document without anyone choosing that — shows up as a deliberate edit to
    this assertion rather than as a green build.
    """
    fields, block = _collect_fields(_entry_body(_BARE_BULLET_FRAGMENT))

    assert not any(_SWALLOWED_TEXT in line for line in block), (
        "strict=False is the pre-existing behavior and is expected to drop the"
        " line; if that changed, this test is the place to record the decision"
    )
    assert "glued onto `Migration`" in fields["Migration"], (
        "the damage is the point: the indented lines under the dropped bullet"
        " land on the PREVIOUS field's value, which is how a published note"
        f" ends up a sentence fragment. Migration reads: {fields['Migration']!r}"
    )


def test_the_shipped_fragment_dir_is_the_one_the_walk_reads() -> None:
    """The walk reads the tree this repository ships, not a copy."""
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    expected = repo_root / "docs" / "surface-changes"
    assert expected.is_dir()
    assert all(path.parent == expected for path in fragment_paths()), (
        "fragment_paths() must read docs/surface-changes/ under this"
        " repository root; a walk rooted anywhere else would let the ratchet"
        " above pass over the wrong tree"
    )
