"""D-14 — the rename-and-removal gate, proven live rather than assumed.

D-14 makes mkdocstrings' own strict-mode collection failure the WHOLE
rename-and-removal gate. There is no extra tooling: no manifest of documented
identifiers, no cross-check script, no lint. If a Protocol under `src/` or
`runtime/` is renamed or deleted while a page still names it, the `:::`
directive fails to collect, mkdocstrings emits a warning, and `strict: true`
turns that warning into a nonzero exit.

That is an attractive design precisely because it is free — and it is exactly
the kind of gate that quietly stops working. `strict` could be dropped from
`mkdocs.yml`, the handler could be reconfigured to downgrade collection
failures, or a future mkdocstrings release could turn the failure into an INFO
line. In any of those cases the reference pages would keep building green while
describing a surface that no longer exists (threat T-14-30 — a stale page is a
spoofing risk, not a cosmetic one).

This module is the paired positive and negative control for that gate. It runs
the REAL site config against a COPY of the real `public/` tree and asserts:

* an identifier that cannot exist at all fails the build,
* a near-miss RENAME of a genuinely documented identifier also fails it — the
  case that actually happens in practice, and the one a gate keyed on
  "obviously fake name" shapes would miss,
* the unmodified copy builds clean, so the two failures above are attributable
  to the mutation rather than to a broken fixture.

**Why the subprocess runs with the REPO ROOT as its CWD.** Both of the site's
path-resolving settings — `pymdownx.snippets` `base_path` and the mkdocstrings
python handler's `paths: ["src", "runtime"]` — resolve against the PROCESS CWD,
not against the config file's directory. Building from inside a temporary
directory would therefore break every `--8<--` include and every module import
at once, and the clean control would fail for reasons that have nothing to do
with the gate under test. So the copied config keeps the repo root as CWD and
only redirects `docs_dir` and `site_dir` at absolute temporary paths. This is
the shape the plan calls for, and the pitfall it names.

The working tree is never modified: `public/` is COPIED before being mutated,
and the build output goes to a temporary `site_dir`.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The real site config and the real published tree — this test is only
#: meaningful against the shipped configuration, not a reconstruction of it.
REAL_CONFIG = REPO_ROOT / "mkdocs.yml"
REAL_DOCS = REPO_ROOT / "public"

#: A page whose identifiers are curated and stable. Mutations are applied here
#: rather than to a NEW page: `mkdocs.yml` enumerates its nav explicitly, and an
#: unlisted page would emit its own "not in nav" warning — which is also fatal
#: under `strict: true` and would let a dead gate pass for the wrong reason.
TARGET_PAGE = pathlib.Path("reference") / "protocols" / "harness-adapter.md"

#: A genuinely documented identifier on that page, and the near-miss form of it.
REAL_IDENTIFIER = "ccf.harness.protocol.HarnessAdapterProtocol"
RENAMED_IDENTIFIER = REAL_IDENTIFIER + "s"

#: An identifier that cannot resolve under any configuration.
FABRICATED_IDENTIFIER = "ccf.does.not.Exist"

#: The collection failure mkdocstrings reports. Asserted by text, not only by
#: exit status, so an unrelated build break cannot masquerade as the gate firing.
COLLECTION_FAILURE = "Could not collect"

#: Subprocess bound — a hung mkdocs must fail the suite, not stall CI.
BUILD_TIMEOUT_SECONDS = 300


def _stage(tmp_path: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    """Copy `public/` and the real config into `tmp_path`.

    Returns the copied docs tree and the copied config. The config is rewritten
    so `docs_dir` and `site_dir` are ABSOLUTE temporary paths; every other
    setting — `strict`, the handler options, the nav, the snippets config — is
    carried over verbatim, because those are the settings under test.
    """
    docs_dir = tmp_path / "public"
    shutil.copytree(REAL_DOCS, docs_dir)

    site_dir = tmp_path / "site"
    config_text = REAL_CONFIG.read_text(encoding="utf-8")
    assert "\ndocs_dir: public\n" in config_text, "config drifted from fixture"
    assert "\nsite_dir: site\n" in config_text, "config drifted from fixture"
    config_text = config_text.replace(
        "\ndocs_dir: public\n", f"\ndocs_dir: {docs_dir}\n"
    ).replace("\nsite_dir: site\n", f"\nsite_dir: {site_dir}\n")

    config = tmp_path / "mkdocs.yml"
    config.write_text(config_text, encoding="utf-8")
    return docs_dir, config


def _build(config: pathlib.Path) -> subprocess.CompletedProcess[str]:
    """Build the copied site with the REPO ROOT as CWD (see module docstring)."""
    return subprocess.run(
        [sys.executable, "-m", "mkdocs", "build", "--strict", "-f", str(config)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=BUILD_TIMEOUT_SECONDS,
    )


# --- violating case 1: an identifier that cannot exist ----------------------


def test_an_unresolvable_identifier_fails_the_strict_build(
    tmp_path: pathlib.Path,
) -> None:
    docs_dir, config = _stage(tmp_path)
    page = docs_dir / TARGET_PAGE
    page.write_text(
        page.read_text(encoding="utf-8") + f"\n::: {FABRICATED_IDENTIFIER}\n",
        encoding="utf-8",
    )

    result = _build(config)

    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert COLLECTION_FAILURE in output, output


# --- violating case 2: a near-miss rename ----------------------------------


def test_a_renamed_identifier_fails_the_strict_build(
    tmp_path: pathlib.Path,
) -> None:
    """The gate must catch a RENAME, not only an obviously fabricated name.

    A one-character difference from a real, resolvable identifier is the
    realistic drift: somebody renames the Protocol in `src/` and the page keeps
    the old name. If only the fabricated case fired, the gate would be passing
    on the scenario it does not actually cover.
    """
    docs_dir, config = _stage(tmp_path)
    page = docs_dir / TARGET_PAGE
    original = page.read_text(encoding="utf-8")
    assert f"::: {REAL_IDENTIFIER}" in original, "fixture drifted from its page"
    page.write_text(
        original.replace(REAL_IDENTIFIER, RENAMED_IDENTIFIER), encoding="utf-8"
    )

    result = _build(config)

    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert COLLECTION_FAILURE in output, output


# --- clean case ------------------------------------------------------------


def test_the_unmodified_tree_builds_clean(tmp_path: pathlib.Path) -> None:
    """Without this control the two failures above prove nothing."""
    _docs_dir, config = _stage(tmp_path)

    result = _build(config)

    assert result.returncode == 0, result.stdout + result.stderr
