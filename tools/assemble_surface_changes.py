"""D-15 — assemble the curated surface-change log from its per-plan fragments.

D-15 asks for two halves of one guarantee. ``tools/dump_surface.py`` is the
*generated* half: a machine-derived manifest of every public name in ``/src``
and ``/runtime``, so a removed or reshaped export cannot slip through
unnoticed. This module is the *curated* half's assembler: it concatenates the
``docs/surface-changes/15-*.md`` fragments each plan wrote as it landed into
one ``docs/SURFACE-CHANGES.md`` — the migration note D-15B promises anyone
building against v0.1/v0.2, and the document Phase 16 consumes directly.

Why fragments, and why assembly is a tool
-----------------------------------------

D-15 requires the curated log be written **incrementally, as plans land**: a
log assembled retroactively at phase close is a log written *from* the diff,
which is exactly the thing it is supposed to add information to. But Phase 15
executes in parallel waves, and a single hand-edited ``SURFACE-CHANGES.md``
would have serialized fourteen waves for a documentation reason. So each plan
owns one fragment and this tool joins them — deterministically, so the joined
document is reviewable as a diff and its staleness is detectable.

This follows ``tools/dump_openapi.py`` exactly: ``REPO_ROOT`` from ``__file__``
rather than ``Path.cwd()``, an exported :func:`serialize` the drift assertion
imports rather than restating, and a ``--check`` mode that writes nothing and
exits 1 naming ``make surface-changes`` as the fix.

The seven fields, and why the assembler refuses without them
------------------------------------------------------------

Every entry carries ``Surface``, ``Public surface``, ``Change type``,
``Before``, ``After``, ``Why`` and ``Migration``
(``docs/surface-changes/README.md``). A fragment missing ``Why`` or
``Migration`` ships a migration note an adopter cannot act on, so it fails the
build rather than being assembled into one. ``Public surface`` must parse to
exactly ``true`` or ``false``: a third value would silently opt the entry out
of **both** directions of ``tests/test_surface_completeness.py``'s cross-check,
turning a checked classification into an escape hatch.

A section is recognised as an *entry* by carrying at least one of the seven
field bullets; a section carrying some but not all of them is a build failure.
Fragments legitimately also carry prose sections (rulings, verification notes),
and those are passed over — but a genuine entry that lost its ``Surface`` line
must not be quietly demoted to prose, which is what the some-but-not-all rule
prevents.

:func:`parse_entries` is exported so the phase-close completeness test reads the
log through **the same parser that assembles it**. A second Markdown scraper
would be a second definition of "what the log says", and the two would
eventually disagree about which entries exist.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

#: The per-plan fragments. One file per plan, named ``15-NN-<slug>.md``.
FRAGMENT_DIR = REPO_ROOT / "docs" / "surface-changes"

#: The assembled curated log — the D-15B migration note, handed to Phase 16.
OUTPUT_PATH = REPO_ROOT / "docs" / "SURFACE-CHANGES.md"

#: The seven fields every entry carries (``docs/surface-changes/README.md``).
FIELDS: tuple[str, ...] = (
    "Surface",
    "Public surface",
    "Change type",
    "Before",
    "After",
    "Why",
    "Migration",
)

#: The four change types. ``behavior`` exists because a signature diff cannot
#: see a change like D-02's to ``load_artifact``'s return values.
CHANGE_TYPES: tuple[str, ...] = ("added", "reshaped", "removed", "behavior")

_SECTION_TITLES: dict[str, str] = {
    "added": "Added",
    "reshaped": "Reshaped",
    "removed": "Removed",
    "behavior": "Behavior changes",
}

_SECTION_BLURBS: dict[str, str] = {
    "added": (
        "Surfaces that did not exist at phase start. Nothing here breaks an"
        " existing integration; every entry is a path that is now available."
    ),
    "reshaped": (
        "Surfaces that still exist under the same name but whose shape moved."
        " These are the entries an existing integration must read."
    ),
    "removed": (
        "Surfaces that no longer exist. Each entry names what replaces it."
    ),
    "behavior": (
        "Surfaces whose **signature did not move** but whose observable"
        " behavior did. A generated signature diff is structurally incapable"
        " of seeing these, which is why D-15 asks for a curated log alongside"
        " the manifest rather than instead of it."
    ),
}

_FRAGMENT_HEADING = re.compile(r"^## +(?P<title>.+?)\s*$")
_FIELD_BULLET = re.compile(r"^- +(?P<field>[A-Z][A-Za-z ]*?): *(?P<value>.*)$")
_PLAN_NUMBER = re.compile(r"^15-(?P<plan>\d+)-")

REGENERATION_COMMAND = "make surface-changes"


class FragmentError(ValueError):
    """A fragment the assembler refuses to assemble into a migration note."""


def fragment_paths() -> list[pathlib.Path]:
    """Every fragment, in plan-number order.

    Sorted numerically rather than lexically so a hypothetical two-digit and
    three-digit plan set would not interleave, and so the assembled document's
    order matches the order the phase actually executed in.
    """
    if not FRAGMENT_DIR.is_dir():
        return []

    def key(path: pathlib.Path) -> tuple[int, str]:
        match = _PLAN_NUMBER.match(path.name)
        return (int(match.group("plan")) if match else 0, path.name)

    return sorted(FRAGMENT_DIR.glob("15-*.md"), key=key)


def _split_sections(text: str) -> list[tuple[str, list[str]]]:
    """``## `` sections of one fragment as ``(title, body lines)``."""
    sections: list[tuple[str, list[str]]] = []
    title: str | None = None
    body: list[str] = []
    for line in text.splitlines():
        heading = _FRAGMENT_HEADING.match(line)
        if heading is not None:
            if title is not None:
                sections.append((title, body))
            title = heading.group("title")
            body = []
            continue
        if title is not None:
            body.append(line)
    if title is not None:
        sections.append((title, body))
    return sections


def _collect_fields(body: list[str]) -> tuple[dict[str, str], list[str]]:
    """Field name -> value, plus the verbatim bullet block.

    A field's value may continue onto indented lines; the continuation is
    joined with a single space so ``Surface`` is comparable as a token while
    ``Why`` and ``Migration`` stay readable. The verbatim block is kept
    separately because the assembled document re-emits the author's own
    line breaks rather than reflowing their prose.
    """
    fields: dict[str, str] = {}
    block: list[str] = []
    current: str | None = None
    for line in body:
        bullet = _FIELD_BULLET.match(line)
        if bullet is not None:
            current = bullet.group("field")
            fields[current] = bullet.group("value").strip()
            block.append(line)
            continue
        if current is not None and line.strip() and line.startswith((" ", "\t")):
            fields[current] = f"{fields[current]} {line.strip()}".strip()
            block.append(line)
            continue
        if current is not None and not line.strip():
            # A blank line ends the bullet block; anything after it is prose
            # the entry carries as commentary, not another field.
            current = None
    return fields, block


def _normalize_public_surface(raw: str, where: str) -> bool:
    """``true``/``false`` and nothing else.

    A third value would opt the entry out of both directions of the
    phase-close cross-check at once, which is precisely the escape hatch the
    classification is not allowed to be.
    """
    value = raw.strip().lower()
    if value == "true":
        return True
    if value == "false":
        return False
    raise FragmentError(
        f"{where}: `Public surface` is {raw!r}; it must be exactly `true` or"
        " `false`. A third value opts the entry out of both directions of"
        " tests/test_surface_completeness.py's cross-check, which turns a"
        " checked classification into an escape hatch."
    )


def parse_entries() -> list[dict[str, object]]:
    """Every entry in every fragment, validated, in plan-number order.

    Each dict carries the seven fields plus ``fragment`` (the source file
    name), ``heading`` (the section title) and ``block`` (the verbatim bullet
    lines). ``Public surface`` is normalized to a Python ``bool`` so callers
    partition on a boolean rather than re-deriving one from a string.

    ``tests/test_surface_completeness.py`` reads the curated log through this
    function rather than scraping the assembled Markdown, so the log's meaning
    has exactly one definition.
    """
    entries: list[dict[str, object]] = []
    for path in fragment_paths():
        text = path.read_text(encoding="utf-8")
        for title, body in _split_sections(text):
            fields, block = _collect_fields(body)
            present = [name for name in FIELDS if name in fields]
            if not present:
                continue  # a prose section: a ruling, a verification note
            where = f"{path.name} :: ## {title}"
            missing = [name for name in FIELDS if name not in fields]
            if missing:
                raise FragmentError(
                    f"{where}: entry is missing {missing}. Every entry carries"
                    f" all seven fields {list(FIELDS)} — an entry with no"
                    " `Why` or no `Migration` ships a migration note an"
                    " adopter cannot act on."
                )
            change_type = fields["Change type"].strip()
            if change_type not in CHANGE_TYPES:
                raise FragmentError(
                    f"{where}: `Change type` is {change_type!r}; it must be one"
                    f" of {list(CHANGE_TYPES)}."
                )
            public = _normalize_public_surface(fields["Public surface"], where)
            surface = fields["Surface"].strip()
            if public and len(surface.split()) != 1:
                raise FragmentError(
                    f"{where}: a `Public surface: true` entry's `Surface` must"
                    " be the fully dotted, fully-qualified name as a single"
                    f" token, never prose — got {surface!r}. The phase-close"
                    " cross-check matches that string literally against the"
                    " generated manifest diff."
                )
            entries.append(
                {
                    "fragment": path.name,
                    "heading": title,
                    "block": "\n".join(block),
                    **{name: fields[name] for name in FIELDS},
                    "Surface": surface,
                    "Change type": change_type,
                    "Public surface": public,
                }
            )
    return entries


def _render_entry(entry: dict[str, object]) -> list[str]:
    lines = [f"#### {entry['heading']}", ""]
    lines.extend(str(entry["block"]).splitlines())
    lines.extend(["", f"*Recorded by `{entry['fragment']}`.*", ""])
    return lines


def _render_group(entries: list[dict[str, object]], heading: str) -> list[str]:
    lines: list[str] = []
    for entry in entries:
        lines.extend(_render_entry(entry))
    if not lines:
        return []
    return [f"### {heading}", ""] + lines


def serialize(entries: list[dict[str, object]] | None = None) -> str:
    """The assembled document — the one rendering recipe.

    ``tests/test_surface_drift.py`` imports this rather than restating it, so
    the committed file and the drift assertion cannot disagree about what the
    log is.
    """
    if entries is None:
        entries = parse_entries()

    public_count = sum(1 for entry in entries if entry["Public surface"])
    lines: list[str] = [
        "# Surface changes — Phase 15 (SDK Ergonomics)",
        "",
        "<!--",
        "  GENERATED — do not edit this file by hand.",
        "  Assembled from docs/surface-changes/15-*.md by",
        "  tools/assemble_surface_changes.py. To change anything here, edit the",
        f"  owning fragment and re-run `{REGENERATION_COMMAND}`.",
        "-->",
        "",
        "## What this document is",
        "",
        "This is the **migration note D-15B promises**. D-15B took free rein on"
        " the public API pre-1.0 on the explicit understanding that anyone"
        " building against v0.1 or v0.2 gets a migration; this is it. Every"
        " surface Phase 15 added, reshaped, removed, or changed the behavior of"
        " is recorded below with the reason it moved and what an adopter has to"
        " do about it.",
        "",
        "It is assembled from the per-plan fragments under"
        " `docs/surface-changes/`, which each plan wrote **as it landed**. A"
        " migration note written retroactively at phase close is a note written"
        " from the diff, which is the one thing it is supposed to add"
        " information to.",
        "",
        "**The `Behavior changes` section is why this document exists at all.**"
        " `docs/surface/v0.2-surface.json` is generated from every module's"
        " `__all__` and records signatures; it is structurally incapable of"
        " seeing a change like D-02's, where `load_artifact` kept its signature"
        " and changed what it returns for a timestamp-shaped scalar. A"
        " generated diff and a curated log are two halves of one guarantee, and"
        " `tests/test_surface_completeness.py` asserts they agree.",
        "",
        "**Phase 16 consumes this document directly.** The documentation"
        " rewrite describes the surface that exists; this is the record of how"
        " it got there from the surface Phase 14 documented.",
        "",
        "## How to read an entry",
        "",
        "Every entry carries seven fields: `Surface`, `Public surface`,"
        " `Change type`, `Before`, `After`, `Why`, and `Migration`. The"
        " assembler refuses to build this document from an entry missing any of"
        " them.",
        "",
        "`Public surface: true` means the entry names an exported Python name"
        " and appears in the generated manifest diff. `Public surface: false`"
        " entries are real changes an adopter must act on that are **not**"
        " Python API — lint scope, tooling, committed schemas, and artifact"
        " *document formats*. They are grouped separately under each change"
        " type so a Python API change is never mistaken for a YAML reshape."
        " The classification is checked in both directions by"
        " `tests/test_surface_completeness.py`: a public change mislabelled"
        " non-public fails, and a non-public entry whose name turns up in the"
        " manifest diff fails too.",
        "",
        f"**{len(entries)} entries**, of which **{public_count}** name a public"
        " Python surface.",
        "",
    ]

    for change_type in CHANGE_TYPES:
        of_type = [e for e in entries if e["Change type"] == change_type]
        public = [e for e in of_type if e["Public surface"]]
        non_public = [e for e in of_type if not e["Public surface"]]
        lines.extend(
            [
                f"## {_SECTION_TITLES[change_type]}",
                "",
                _SECTION_BLURBS[change_type],
                "",
                f"{len(of_type)} entries — {len(public)} public Python surface,"
                f" {len(non_public)} not public Python API.",
                "",
            ]
        )
        if not of_type:
            lines.extend(["*No entries.*", ""])
            continue
        lines.extend(_render_group(public, "Public Python surface"))
        lines.extend(
            _render_group(non_public, "Not public Python API")
        )

    return "\n".join(lines).rstrip("\n") + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Assemble docs/SURFACE-CHANGES.md from the per-plan"
            " docs/surface-changes/ fragments (D-15)."
        )
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Write nothing; exit 1 if the on-disk document differs from what"
            " the fragments assemble to."
        ),
    )
    args = parser.parse_args(argv)

    try:
        emitted = serialize()
    except FragmentError as error:
        print(f"surface-change fragment refused: {error}", file=sys.stderr)
        return 1

    if args.check:
        on_disk = (
            OUTPUT_PATH.read_text(encoding="utf-8")
            if OUTPUT_PATH.exists()
            else ""
        )
        if on_disk != emitted:
            print(
                f"{OUTPUT_PATH} differs from what the fragments under"
                f" {FRAGMENT_DIR} assemble to. Run"
                f" `{REGENERATION_COMMAND}` and commit the result — a fragment"
                " added without reassembly leaves the migration note"
                " incomplete, which is the one failure this document cannot"
                " afford.",
                file=sys.stderr,
            )
            return 1
        return 0

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(emitted, encoding="utf-8")
    print(f"wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
