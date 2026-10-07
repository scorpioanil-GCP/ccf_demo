"""SEC-027 (``D-IMPL-376`` ruling 4): the SDK's distribution is ``ccf-sdk``, never ``ccf``.

``ccf`` on public PyPI is Microsoft's Confidential Consortium Framework
(7.0.18, measured 2026-10-07), so a distribution named ``ccf`` is a
dependency-confusion path: ``pip install ccf`` installs Microsoft's package,
and a self-referencing extra spelled ``ccf[...]`` resolves to it the moment the
project stops being named ``ccf``. A reader that looks the SDK's OWN installed
metadata up by the name ``ccf`` reads Microsoft's metadata whenever that
package is installed — and the runtime reader feeds the built-in adapter's
replay pin (``src/ccf/graph/registry.py::_sdk_version`` into
``src/ccf/graph/registry.py::ResolvedBackend``, then
``src/ccf/graph/registry.py::AdapterPin`` and replay dimension 2's
``graph_adapter_version``), so a decision record would carry Microsoft's
version as the SDK's.

The IMPORT name stays ``ccf``; only the distribution name changes. Four
checks, two of them behavioral:

1. the package metadata (``[project] name`` in ``pyproject.toml``) is
   ``ccf-sdk``, and no requirement the project declares names the PyPI
   project ``ccf``;
2. every reader of the SDK's own installed metadata names that one declared
   distribution — the runtime reader
   (``src/ccf/graph/registry.py::SDK_DISTRIBUTION``) and the release version
   gate (``tools/check_version_stamp.py::DISTRIBUTION``);
3. the runtime reader, behaviorally: with a distribution named ``ccf`` (the
   shape Microsoft's wheel installs) AND one named ``ccf-sdk`` on
   ``sys.path``, the built-in adapter's resolved pin carries the ``ccf-sdk``
   version and distribution;
4. the version gate, behaviorally: with only a distribution named ``ccf``
   visible it refuses — it found no SDK distribution — rather than certifying
   Microsoft's version; with a ``ccf-sdk`` distribution visible it reads that
   one.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

import tools.check_version_stamp as version_gate
from ccf.graph.registry import SDK_DISTRIBUTION, resolve

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PYPROJECT = _REPO_ROOT / "pyproject.toml"
_GATE = _REPO_ROOT / "tools" / "check_version_stamp.py"

#: The distribution name this SDK publishes under (SEC-027).
EXPECTED_DISTRIBUTION = "ccf-sdk"

#: The PyPI project that is NOT this SDK: Microsoft's Confidential Consortium
#: Framework, which also installs a top-level ``ccf`` import package.
FOREIGN_DISTRIBUTION = "ccf"
FOREIGN_VERSION = "7.0.18"

#: A version no real install carries, so reading it proves which distribution
#: the reader chose.
PROBE_SDK_VERSION = "9.9.9"

#: The built-in adapter every development checkout boots against.
BUILTIN_ADAPTER = "sqlite"

_GIT_IDENTITY_ENV = {
    "GIT_AUTHOR_NAME": "distribution-name-test",
    "GIT_AUTHOR_EMAIL": "distribution-name-test@example.invalid",
    "GIT_COMMITTER_NAME": "distribution-name-test",
    "GIT_COMMITTER_EMAIL": "distribution-name-test@example.invalid",
}


def _project() -> dict[str, object]:
    document = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    project = document["project"]
    assert isinstance(project, dict)
    return project


def _declared_requirements(project: dict[str, object]) -> list[tuple[str, str]]:
    """``(where, requirement)`` for every requirement ``[project]`` declares."""
    found: list[tuple[str, str]] = []
    dependencies = project.get("dependencies", [])
    assert isinstance(dependencies, list)
    found.extend(("[project].dependencies", str(raw)) for raw in dependencies)
    optional = project.get("optional-dependencies", {})
    assert isinstance(optional, dict)
    for extra, requirements in optional.items():
        assert isinstance(requirements, list)
        found.extend(
            (f"[project.optional-dependencies].{extra}", str(raw)) for raw in requirements
        )
    return found


def _write_installed_distribution(root: Path, name: str, version: str) -> None:
    """Write one installed distribution's metadata directory, the way a wheel install does.

    The directory stem is the escaped name (``-`` becomes ``_``), as the wheel
    specification requires and as ``pip`` writes it; the ``Name:`` field is the
    distribution name itself.
    """
    stem = name.replace("-", "_")
    info = root / f"{stem}-{version}.dist-info"
    info.mkdir(parents=True)
    (info / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n", encoding="utf-8"
    )


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
        env={**os.environ, **_GIT_IDENTITY_ENV},
    )


def _off_tag_repo(root: Path) -> Path:
    """A repository with a release tag one commit behind HEAD: the gate's ordinary posture."""
    repo = root / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "a.txt").write_text("a\n", encoding="utf-8")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-q", "-m", "one")
    _git(repo, "tag", "v1.0.0")
    (repo / "b.txt").write_text("b\n", encoding="utf-8")
    _git(repo, "add", "b.txt")
    _git(repo, "commit", "-q", "-m", "two")
    return repo


def _run_gate(cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run the real gate script, isolated from this environment's own installs.

    ``-S`` skips ``site``, so no installed ``ccf`` or ``ccf-sdk`` in this
    interpreter's ``site-packages`` is visible; the gate sees only what the
    scenario wrote into ``cwd``, which the gate itself puts on ``sys.path``.
    """
    return subprocess.run(
        [sys.executable, "-S", str(_GATE)],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=15,
        env={"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "/tmp")},
    )


def test_the_package_metadata_names_the_distribution_ccf_sdk() -> None:
    assert _project()["name"] == EXPECTED_DISTRIBUTION


def test_no_declared_requirement_names_the_foreign_pypi_project_ccf() -> None:
    """A self-referencing extra spelled ``ccf[...]`` is a dependency on Microsoft's package.

    Once the project is named ``ccf-sdk``, a requirement whose name
    canonicalizes to ``ccf`` no longer refers to this project; pip resolves it
    from the index, where ``ccf`` is Microsoft's.
    """
    project = _project()
    requirements = _declared_requirements(project)
    offenders = [
        (where, raw)
        for where, raw in requirements
        if canonicalize_name(Requirement(raw).name) == FOREIGN_DISTRIBUTION
    ]
    assert offenders == [], offenders
    # Non-vacuity: the project's own aggregate extras (`dev`, `harnesses`) are
    # self-references, so the scan above read requirements that name the
    # project — under its declared name.
    own = canonicalize_name(str(project["name"]))
    self_references = [
        raw for _, raw in requirements if canonicalize_name(Requirement(raw).name) == own
    ]
    assert self_references, "no self-referencing extra found; the scan read nothing"


def test_every_reader_of_the_sdks_own_metadata_names_the_declared_distribution() -> None:
    readers = {
        "src/ccf/graph/registry.py::SDK_DISTRIBUTION": SDK_DISTRIBUTION,
        "tools/check_version_stamp.py::DISTRIBUTION": version_gate.DISTRIBUTION,
    }
    declared = _project()["name"]
    assert readers == {reader: declared for reader in readers}
    assert declared == EXPECTED_DISTRIBUTION


def test_the_builtin_adapter_pin_reads_ccf_sdk_and_never_a_distribution_named_ccf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both shapes on ``sys.path`` ahead of every real install; the pin must pick ``ccf-sdk``.

    Before the rename the reader looked the SDK up as ``ccf`` and returned the
    foreign distribution's version — the value replay dimension 2 records as
    ``graph_adapter_version``.
    """
    site = tmp_path / "site"
    _write_installed_distribution(site, FOREIGN_DISTRIBUTION, FOREIGN_VERSION)
    _write_installed_distribution(site, EXPECTED_DISTRIBUTION, PROBE_SDK_VERSION)
    monkeypatch.syspath_prepend(str(site))

    record = resolve(BUILTIN_ADAPTER)

    assert (record.distribution, record.version) == (EXPECTED_DISTRIBUTION, PROBE_SDK_VERSION)


def test_the_version_gate_refuses_when_only_a_distribution_named_ccf_is_visible(
    tmp_path: Path,
) -> None:
    """Microsoft's ``ccf`` alone is not the SDK; the gate must find no SDK and refuse."""
    repo = _off_tag_repo(tmp_path)
    _write_installed_distribution(repo, FOREIGN_DISTRIBUTION, FOREIGN_VERSION)

    result = _run_gate(repo)

    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stdout.strip() == (
        f"check_version_stamp: no {EXPECTED_DISTRIBUTION!r} distribution found on sys.path"
    )


def test_the_version_gate_reads_the_ccf_sdk_distribution_beside_a_foreign_ccf(
    tmp_path: Path,
) -> None:
    repo = _off_tag_repo(tmp_path)
    _write_installed_distribution(repo, FOREIGN_DISTRIBUTION, FOREIGN_VERSION)
    _write_installed_distribution(repo, EXPECTED_DISTRIBUTION, PROBE_SDK_VERSION)

    result = _run_gate(repo)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == (
        "check_version_stamp: HEAD is not an exact 'v[0-9]*' tag; installed"
        f" {EXPECTED_DISTRIBUTION} is {PROBE_SDK_VERSION} — nothing to hold"
    )
