"""`docs/SURFACE-AUDIT.md` §5.3 — one gate per advisory this phase discharges.

Four advisories were carried out of Phase 15 into Phase 16, and all four are
prose obligations. Prose obligations are the ones a green build cannot speak
to: `make docs-strict` green means the site *builds*, not that it is *current*
— which is A-3's own finding, and the reason a per-advisory gate exists at all
rather than a note in a summary saying the pages were rewritten.

Each test below is named for the advisory it proves, reports that advisory by
name on failure, and is written so that reverting the page it protects turns it
red. That last property is the one that is easy to lose: an assertion phrased
as "the page exists" survives the page being gutted.

The four, in the audit's own words:

``A-1``
    Package re-exports mean one added name can be listed twice, so a migration
    note reads as twice as many new concepts. Document ``from ccf.deployment
    import …`` as the single preferred day-1 import and treat submodule
    fully-qualified names as implementation detail.
``A-2``
    No published fragment covers the surface toolchain itself — the generator,
    ``make surface``, and baseline immutability.
``A-3``
    The published docs still describe the pre-15 surface.
``A-8``
    "``role`` governs registration and pinning, never visibility" is subtle and
    needs explicit documentation — **both** halves of it.

Two shapes are worth explaining before they surprise a reader.

**A-3's signature half tracks the code, not a transcription.** Asserting that
some published page contains a hand-copied parameter list would rot the moment
the signature changed, and would rot *silently*, which is the defect class A-3
is. So documented ``boot(`` invocations are extracted from published code
contexts and their keyword names are compared against
``inspect.signature(ccf.boot.boot)`` at run time. **Measured at this plan's
HEAD: zero published pages carry a ``boot(`` invocation with arguments**, so
the assertion currently passes over an empty set on purpose — the pre-15
``boot(database_path=…)`` form was removed, and nothing has replaced it in
prose. Non-vacuity is therefore proven by a control that injects a stale
signature rather than by a floor on the corpus, because a floor here would
demand a page write a call it has no reason to write.

**The known limit of that half**, stated rather than discovered later: it reads
the *source* Markdown, so a ``boot(`` call reaching a page through a snippet
include is not seen. That case is covered from the other side — an included
call is real example code, which the always-on example suite runs.

**Nav membership is parsed, not assumed.** `mkdocs.yml` enumerates every page
explicitly with no globs, and `validation.nav.omitted_files` under ``--strict``
already fails a page absent from nav. This module still checks it, for the
`test_no_stale_example_paths` reason: the two gates should agree, and a failure
here that names the page and the advisory is more useful than a build warning.
The config is not `yaml.safe_load`ed — it carries a ``!!python/name:`` tag that
the safe loader refuses — so the nav block is sliced and its page paths read
off directly.
"""

from __future__ import annotations

import inspect
import pathlib
import re
import shutil

import pytest

from tools.docs_tests import _prose
from tools.publish_scan import RULE_INTERNAL_PATH, scan_prebuild

MKDOCS_CONFIG = _prose.REPO_ROOT / "mkdocs.yml"
EXAMPLES_DIR = _prose.REPO_ROOT / "examples"

#: The page each advisory's prose obligation lands on, relative to `public/`.
A1_PAGE = "reference/artifacts/deployment-manifest.md"
A2_PAGE = "reference/surface-toolchain.md"
A8_PAGE = "reference/artifacts/deployment-manifest.md"

#: A-1's preferred spelling, and the spelling it displaces. The second is a
#: *regex*: any submodule of the wiring package, not one named module, because
#: naming one would leave the other four unguarded.
PREFERRED_IMPORT = "from ccf.deployment import"
SUBMODULE_IMPORT = re.compile(r"from\s+ccf\.deployment\.[A-Za-z_][A-Za-z0-9_]*\s+import")

#: A-2's page must name its subject matter, not merely exist.
A2_REQUIRED_TOKENS: tuple[str, ...] = (
    "tools/dump_surface.py",
    "make surface",
    "tools/assemble_surface_changes.py",
)

#: The claim A-2 exists to get written down, in the page's own words.
A2_IMMUTABILITY_MARKERS: tuple[str, ...] = ("exactly twice", "immutab")

#: A-3's floor: the published tree must speak the vocabulary of the surface
#: that shipped in Phases 15.2–15.4. Every one of these was measured at **zero**
#: occurrences across `public/` when the audit was written.
A3_REQUIRED_TOKENS: tuple[str, ...] = (
    "load_and_boot",
    "backend",
    "ccf backends",
    "GraphQuery",
    "registry",
)

#: A-8's two halves. The first alone is the mislead: an artifact that is
#: reachable reads as an artifact that was registered.
A8_REACHABILITY = "BootedFabric.artifacts"
A8_ABSENCE: tuple[str, ...] = (
    "absent from `pins`",
    "absent from replay dimension 2",
)

#: A ``boot(`` invocation, with the leading boundary that stops it matching the
#: tail of ``load_and_boot(``.
BOOT_CALL = re.compile(r"(?<![A-Za-z0-9_.])boot\s*\(")

#: A keyword argument's name inside an extracted call.
KEYWORD = re.compile(r"(?:^|[,(])\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(?!=)")

#: The nav block: from the top-level ``nav:`` key to the next top-level key, or
#: to end of file — `nav:` is last in `mkdocs.yml` today, and a lookahead that
#: only accepted a following key would silently parse nothing if it stayed last.
NAV_BLOCK = re.compile(r"^nav:\s*$(?P<body>.*?)(?=^\S|\Z)", re.MULTILINE | re.DOTALL)

#: One nav entry's page path.
NAV_PAGE = re.compile(r":\s*([A-Za-z0-9_][A-Za-z0-9_./-]*\.md)\s*$", re.MULTILINE)


# --------------------------------------------------------------------------
# Readers.
# --------------------------------------------------------------------------


def nav_pages(config_text: str) -> set[str]:
    """Every page path enumerated in `mkdocs.yml`'s nav, `public/`-relative."""
    block = NAV_BLOCK.search(config_text)
    if block is None:
        return set()
    return set(NAV_PAGE.findall(block.group("body")))


def _config_text() -> str:
    return MKDOCS_CONFIG.read_text(encoding="utf-8")


def _python_sources(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted(root.rglob("*.py"))


def submodule_import_sites(
    pages: list[pathlib.Path], sources: list[pathlib.Path]
) -> list[str]:
    """`path:line` for every submodule-spelled import of the wiring package."""
    offenders: list[str] = []
    for path in [*pages, *sources]:
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if SUBMODULE_IMPORT.search(line):
                offenders.append(f"{_prose.relative(path)}:{lineno}")
    return offenders


def pages_naming(pages: list[pathlib.Path], token: str) -> list[str]:
    """Every page whose raw text contains `token`."""
    return sorted(
        {
            _prose.relative(page)
            for page, paragraph in _prose.iter_paragraphs(pages, prose_only=False)
            if token in paragraph.raw
        }
    )


def _balanced_argument_text(text: str, open_index: int) -> str | None:
    """The text between `text[open_index]`'s parentheses, or `None` if unclosed."""
    depth = 0
    for index in range(open_index, len(text)):
        character = text[index]
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth == 0:
                return text[open_index + 1 : index]
    return None


def documented_boot_keywords(pages: list[pathlib.Path]) -> list[tuple[str, str]]:
    """`(site, keyword)` for every keyword name in a published `boot(` call.

    Read from code contexts only — fenced blocks and inline code spans — for
    `test_documented_commands_exist`'s reason: running English prose is not
    where a signature is written, and scanning it harvests noise.
    """
    found: list[tuple[str, str]] = []
    for page, paragraph in _prose.iter_paragraphs(pages, prose_only=False):
        chunks = (
            [paragraph.raw]
            if paragraph.fenced
            else re.findall(r"`([^`]*)`", paragraph.raw)
        )
        site = f"{_prose.relative(page)}:{paragraph.lineno}"
        for chunk in chunks:
            for match in BOOT_CALL.finditer(chunk):
                arguments = _balanced_argument_text(chunk, match.end() - 1)
                if arguments is None:
                    continue
                for keyword in KEYWORD.findall("(" + arguments):
                    found.append((site, keyword))
    return found


def live_boot_parameters() -> frozenset[str]:
    """`ccf.boot.boot`'s parameter names, read at run time."""
    import ccf.boot

    return frozenset(inspect.signature(ccf.boot.boot).parameters)


def stale_boot_signatures(pages: list[pathlib.Path]) -> list[str]:
    """`site -> keyword` for every documented keyword the live signature lacks."""
    live = live_boot_parameters()
    return [
        f"{site} -> {keyword}"
        for site, keyword in documented_boot_keywords(pages)
        if keyword not in live
    ]


def a8_paragraphs(page: pathlib.Path) -> list[_prose.Paragraph]:
    """Every paragraph of `page` asserting the reachability half of A-8."""
    return [
        paragraph
        for paragraph in _prose.page_paragraphs(page)
        if A8_REACHABILITY in paragraph.raw
    ]


def a8_offenders(page: pathlib.Path) -> list[str]:
    """Why `page` fails A-8, or an empty list.

    The two halves must sit in **one** paragraph. Split across a page they are
    two sentences a reader can meet independently, and meeting the first one
    alone is the whole of the mislead.
    """
    candidates = a8_paragraphs(page)
    if not candidates:
        return [f"{_prose.relative(page)}: no paragraph names {A8_REACHABILITY}"]
    for paragraph in candidates:
        if all(marker in paragraph.raw for marker in A8_ABSENCE):
            return []
    missing = sorted(
        {
            marker
            for paragraph in candidates
            for marker in A8_ABSENCE
            if marker not in paragraph.raw
        }
    )
    return [
        f"{_prose.relative(page)}:{candidates[0].lineno}: the paragraph stating "
        f"reachability does not also state absence ({', '.join(missing)})"
    ]


# --------------------------------------------------------------------------
# Preconditions — a vacuous pass is the failure this module exists to prevent.
# --------------------------------------------------------------------------


def test_the_published_tree_and_the_nav_are_populated() -> None:
    assert _prose.PUBLIC_DIR.is_dir(), f"missing published tree: {_prose.PUBLIC_DIR}"
    assert _prose.published_pages(), f"no markdown pages under {_prose.PUBLIC_DIR}"
    assert MKDOCS_CONFIG.is_file(), f"missing site config: {MKDOCS_CONFIG}"
    pages = nav_pages(_config_text())
    assert pages, "no nav entries parsed from mkdocs.yml — the nav block moved"
    assert "index.md" in pages, f"nav parsed but looks wrong: {sorted(pages)[:5]}"


def test_the_walk_does_not_depend_on_the_process_cwd(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WR-04: a CWD-relative walk scans nothing and passes everything."""
    monkeypatch.chdir(tmp_path)
    assert _prose.published_pages(), "the page walk resolved against the CWD"
    assert MKDOCS_CONFIG.is_file(), "the site config resolved against the CWD"
    assert EXAMPLES_DIR.is_dir(), "the examples tree resolved against the CWD"
    assert live_boot_parameters(), "boot's signature could not be read"


# --------------------------------------------------------------------------
# A-1 — the day-1 import convention.
# --------------------------------------------------------------------------


def test_a1_the_preferred_day_one_import_is_documented() -> None:
    pages = pages_naming(_prose.published_pages(), PREFERRED_IMPORT)
    assert pages, (
        "A-1 is undischarged: no published page writes "
        f"`{PREFERRED_IMPORT} …` as the day-1 import"
    )
    assert A1_PAGE in nav_pages(_config_text()), (
        f"A-1's convention page {A1_PAGE} is not in mkdocs nav — it is "
        "published by accident or not at all"
    )


def test_a1_no_submodule_import_is_taught_or_demonstrated() -> None:
    """The other half: a spelling the docs displace must not survive in them.

    `examples/` is in scope because the examples are the snippet source of
    record for the published tree — a submodule import there is a submodule
    import a reader is shown.
    """
    offenders = submodule_import_sites(
        _prose.published_pages(), _python_sources(EXAMPLES_DIR)
    )
    assert not offenders, (
        "A-1 is undischarged: these sites import the wiring package through a "
        "submodule path, which the day-1 convention treats as implementation "
        "detail — " + "; ".join(offenders)
    )


# --------------------------------------------------------------------------
# A-2 — the surface-toolchain maintainer page.
# --------------------------------------------------------------------------


def test_a2_the_maintainer_page_is_published_and_names_its_subject() -> None:
    page = _prose.PUBLIC_DIR / A2_PAGE
    assert page.is_file(), f"A-2 is undischarged: {A2_PAGE} does not exist"
    assert A2_PAGE in nav_pages(_config_text()), (
        f"A-2's page {A2_PAGE} is not in mkdocs nav"
    )
    text = page.read_text(encoding="utf-8")
    missing = [token for token in A2_REQUIRED_TOKENS if token not in text]
    assert not missing, (
        "A-2 is undischarged: the maintainer page does not name "
        + ", ".join(missing)
    )
    assert any(marker in text for marker in A2_IMMUTABILITY_MARKERS), (
        "A-2 is undischarged: the maintainer page does not state baseline "
        "immutability, which is the property that makes a drift assertion mean "
        "anything"
    )


def test_a2_the_maintainer_page_passes_the_publication_scan() -> None:
    """It necessarily names internal tooling, and the scan takes no allowlist."""
    violations = scan_prebuild(_prose.PUBLIC_DIR)
    offending = [
        violation
        for violation in violations
        if RULE_INTERNAL_PATH in violation and A2_PAGE in violation
    ]
    assert not offending, (
        f"A-2's maintainer page trips {RULE_INTERNAL_PATH}, which takes no "
        "allowlist — adjust the wording, there is no exemption to add: "
        + "; ".join(offending)
    )
    assert not violations, (
        "the pre-build publication scan refuses the tree: " + "; ".join(violations)
    )


# --------------------------------------------------------------------------
# A-3 — the published tree describes the surface at HEAD.
# --------------------------------------------------------------------------


def test_a3_the_published_tree_speaks_the_current_surface() -> None:
    pages = _prose.published_pages()
    missing = [token for token in A3_REQUIRED_TOKENS if not pages_naming(pages, token)]
    assert not missing, (
        "A-3 is undischarged: no published page mentions " + ", ".join(missing)
    )


def test_a3_no_documented_boot_signature_disagrees_with_the_code() -> None:
    offenders = stale_boot_signatures(_prose.published_pages())
    assert not offenders, (
        "A-3 is undischarged: published pages document boot() keywords that "
        f"are not parameters of it (live signature: "
        f"{sorted(live_boot_parameters())}) — " + "; ".join(offenders)
    )


# --------------------------------------------------------------------------
# A-8 — role governs registration and pinning, never visibility.
# --------------------------------------------------------------------------


def test_a8_both_halves_are_stated_in_one_paragraph() -> None:
    offenders = a8_offenders(_prose.PUBLIC_DIR / A8_PAGE)
    assert not offenders, (
        "A-8 is undischarged: a page stating only that a `role: load` artifact "
        "is reachable teaches the mislead A-8 exists to close — "
        + "; ".join(offenders)
    )


# --------------------------------------------------------------------------
# Controls — a gate nobody has watched fail is a gate that may check nothing.
# --------------------------------------------------------------------------


def _copy(tmp_path: pathlib.Path, relative: str) -> pathlib.Path:
    source = _prose.PUBLIC_DIR / relative
    assert source.is_file(), f"control fixture source missing: {source}"
    target = tmp_path / pathlib.Path(relative).name
    shutil.copy(source, target)
    return target


def test_the_unmodified_copies_pass(tmp_path: pathlib.Path) -> None:
    """The controls' baseline: every refusal below comes from the mutation."""
    a8 = _copy(tmp_path, A8_PAGE)
    assert a8_offenders(a8) == []
    assert submodule_import_sites([a8], []) == []
    assert stale_boot_signatures([a8]) == []


def test_the_a8_gate_refuses_a_page_that_states_only_reachability(
    tmp_path: pathlib.Path,
) -> None:
    """Strip the absence claim; the reachability sentence survives intact."""
    page = _copy(tmp_path, A8_PAGE)
    text = page.read_text(encoding="utf-8").replace("absent from", "reachable from")
    page.write_text(text, encoding="utf-8")
    assert A8_REACHABILITY in text, "the fixture removed the wrong half"
    offenders = a8_offenders(page)
    assert offenders, "the gate admitted a page stating only the reachable half"


def test_the_a8_gate_refuses_two_halves_split_across_paragraphs(
    tmp_path: pathlib.Path,
) -> None:
    """The scoping rule, held from the failing side."""
    page = tmp_path / "split.md"
    page.write_text(
        "A `role: load` artifact is returned on `BootedFabric.artifacts`.\n"
        "\n"
        "Separately, it is absent from `pins` and absent from replay "
        "dimension 2.\n",
        encoding="utf-8",
    )
    assert a8_offenders(page), "two paragraphs were accepted as one statement"


def test_the_a1_gate_refuses_an_injected_submodule_import(
    tmp_path: pathlib.Path,
) -> None:
    page = _copy(tmp_path, A1_PAGE)
    with page.open("a", encoding="utf-8") as handle:
        handle.write("\n```py\nfrom ccf.deployment.manifest import load_and_boot\n```\n")
    offenders = submodule_import_sites([page], [])
    assert offenders, "the gate admitted a submodule-spelled import"
    assert any(page.name in offender for offender in offenders), offenders


def test_the_a1_gate_refuses_a_submodule_import_in_an_example(
    tmp_path: pathlib.Path,
) -> None:
    """The `examples/` half, which is the half with real source files behind it."""
    source = tmp_path / "run.py"
    source.write_text(
        "from ccf.deployment import load_and_boot\n"
        "from ccf.deployment.pins import ResolvedPins\n",
        encoding="utf-8",
    )
    offenders = submodule_import_sites([], [source])
    assert offenders == [f"{_prose.relative(source)}:2"], offenders


def test_the_a2_gate_refuses_a_page_that_names_nothing(
    tmp_path: pathlib.Path,
) -> None:
    page = tmp_path / "surface-toolchain.md"
    page.write_text("# How the surface record works\n\nIt works.\n", encoding="utf-8")
    text = page.read_text(encoding="utf-8")
    missing = [token for token in A2_REQUIRED_TOKENS if token not in text]
    assert missing == list(A2_REQUIRED_TOKENS), missing
    assert not any(marker in text for marker in A2_IMMUTABILITY_MARKERS)


def test_the_a3_gate_refuses_a_stale_boot_signature(
    tmp_path: pathlib.Path,
) -> None:
    """The pre-15.4 spelling, which is exactly what A-3 found published.

    This is also this half's non-vacuity proof: HEAD carries no `boot(`
    invocation with arguments, so without a control the assertion would be
    passing over an empty set with nobody the wiser.
    """
    page = _copy(tmp_path, A8_PAGE)
    with page.open("a", encoding="utf-8") as handle:
        handle.write('\n```py\nboot(database_path="graph.db", tenant_id="acme")\n```\n')
    offenders = stale_boot_signatures([page])
    assert offenders, "the gate admitted a boot() call with a parameter it lacks"
    assert any("database_path" in offender for offender in offenders), offenders


def test_the_a3_gate_admits_a_correct_boot_signature(
    tmp_path: pathlib.Path,
) -> None:
    """Both polarities: a current call must not be reported.

    Without this the stale-signature control would also pass if the extractor
    reported every keyword it found.
    """
    page = _copy(tmp_path, A8_PAGE)
    live = sorted(live_boot_parameters())
    call = ", ".join(f'{name}="x"' for name in live[:3])
    with page.open("a", encoding="utf-8") as handle:
        handle.write(f"\n```py\nboot({call})\n```\n")
    assert stale_boot_signatures([page]) == []


def test_the_boot_extractor_does_not_match_load_and_boot(
    tmp_path: pathlib.Path,
) -> None:
    """The boundary, held from the side that would produce false positives."""
    page = tmp_path / "call.md"
    page.write_text(
        '```py\nload_and_boot(manifest_path="m.yaml", tenant_id="acme")\n```\n',
        encoding="utf-8",
    )
    assert documented_boot_keywords([page]) == []
